import os
import io
import zipfile
import asyncio
import logging
import traceback
import shutil
import tempfile
from fastapi import HTTPException
from pypdf import PdfReader, PdfWriter
import pikepdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from PIL import Image

try:
    import pillow_avif
except ImportError:
    pass

# Word Document Processing & COM Automation Imports
try:
    from docx import Document
    from docx.enum.section import WD_SECTION
except ImportError:
    Document = None
    WD_SECTION = None

try:
    from docxcompose.composer import Composer
except ImportError:
    Composer = None

try:
    import win32com.client
    import pythoncom
except ImportError:
    win32com = None
    pythoncom = None


def _parse_page_ranges(page_ranges: str, max_pages: int) -> list[int]:
    """
    Parses a string like '1-3,5,7-9' into a list of 0-based page indices.
    """
    indices = []
    if not page_ranges:
        return indices
        
    parts = page_ranges.split(',')
    for part in parts:
        part = part.strip()
        if '-' in part:
            start_str, end_str = part.split('-', 1)
            try:
                start = max(1, int(start_str))
                end = min(max_pages, int(end_str))
                indices.extend(range(start - 1, end))
            except ValueError:
                continue
        else:
            try:
                val = int(part)
                if 1 <= val <= max_pages:
                    indices.append(val - 1)
            except ValueError:
                continue
    return sorted(list(set(indices)))

async def merge_pdfs(file_paths: list[str], output_path: str):
    """Combines multiple PDFs into a single PDF."""
    writer = PdfWriter()
    for path in file_paths:
        writer.append(path)
        
    with open(output_path, "wb") as f:
        writer.write(f)
    writer.close()

async def split_pdf(file_path: str, page_ranges: str, output_path: str):
    """Extracts specific page ranges into a new PDF."""
    with open(file_path, "rb") as f_in:
        reader = PdfReader(f_in)
        writer = PdfWriter()
        
        max_pages = len(reader.pages)
        indices = _parse_page_ranges(page_ranges, max_pages)
        
        if not indices:
            raise HTTPException(status_code=400, detail="No valid pages selected for splitting. Please check your page ranges.")
            
        for i in indices:
            writer.add_page(reader.pages[i])
            
        with open(output_path, "wb") as f_out:
            writer.write(f_out)

async def compress_pdf(file_path: str, output_path: str, compression_level: str = "recommended"):
    """
    Compresses PDF using Ghostscript as the primary lossy compression engine with cross-platform binary support.
    
    NOTE: Ghostscript ('gs', 'gswin64c', or 'gswin32c') must be installed on the host OS / server for Ghostscript lossy compression.
    If Ghostscript is not found or fails, automatically falls back to PyMuPDF + pikepdf dual-pass compression.
    
    Ghostscript Presets:
    - 'extreme'     -> -dPDFSETTINGS=/screen  (72 DPI raster downsampling, lowest file size)
    - 'recommended' -> -dPDFSETTINGS=/ebook   (150 DPI raster downsampling, balanced quality)
    - 'low'         -> -dPDFSETTINGS=/printer (300 DPI raster downsampling, high quality)
    """
    import subprocess
    import shutil

    def _do_compress():
        # --- PRIMARY ENGINE: Ghostscript ---
        # Detect Ghostscript executable on host OS (Linux/macOS 'gs', Windows 'gswin64c' / 'gswin32c')
        gs_executable = None
        for cmd in ["gswin64c", "gswin32c", "gs"]:
            if shutil.which(cmd):
                gs_executable = cmd
                break

        # Map preset levels to Ghostscript PDFSETTINGS
        gs_settings = {
            "extreme": "/screen",
            "low": "/printer",
            "recommended": "/ebook"
        }.get(compression_level, "/ebook")

        if gs_executable:
            gs_cmd = [
                gs_executable,
                "-dNOPAUSE",
                "-dBATCH",
                "-dQUIET",
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                f"-dPDFSETTINGS={gs_settings}",
                "-dCompressFonts=true",
                "-dSubsetFonts=true",
                "-dAutoRotatePages=/None",
                f"-sOutputFile={output_path}",
                file_path
            ]
            try:
                result = subprocess.run(gs_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
                if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    # Check if output is actually smaller or valid
                    if os.path.getsize(output_path) <= os.path.getsize(file_path):
                        return
            except Exception:
                # If Ghostscript fails or times out, proceed to Python fallback below
                pass

        # --- SECONDARY ENGINE / FALLBACK: PyMuPDF + pikepdf Dual-Pass ---
        import fitz  # PyMuPDF
        
        original_size = os.path.getsize(file_path)
        temp_pass1_path = output_path + ".pass1.tmp"
        
        if compression_level == "extreme":
            jpg_quality = 50
            max_dim = 1000
        elif compression_level == "low":
            jpg_quality = 80
            max_dim = 1800
        else:  # recommended
            jpg_quality = 65
            max_dim = 1400

        try:
            doc = fitz.open(file_path)
            
            for page_index in range(len(doc)):
                page = doc[page_index]
                image_list = page.get_images(full=True)
                
                for img_info in image_list:
                    xref = img_info[0]
                    try:
                        base_image = doc.extract_image(xref)
                        if not base_image:
                            continue
                        
                        image_bytes = base_image["image"]
                        pil_img = Image.open(io.BytesIO(image_bytes))
                        width, height = pil_img.size
                        
                        if width > max_dim or height > max_dim:
                            pil_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

                        if pil_img.mode in ("RGBA", "P"):
                            pil_img = pil_img.convert("RGB")
                        
                        out_buffer = io.BytesIO()
                        pil_img.save(out_buffer, format="JPEG", quality=jpg_quality, optimize=True)
                        out_bytes = out_buffer.getvalue()
                        
                        if len(out_bytes) < len(image_bytes):
                            page.replace_image(xref, stream=out_bytes)
                    except Exception:
                        continue

            doc.save(
                temp_pass1_path,
                garbage=4,
                deflate=True,
                deflate_images=True,
                deflate_fonts=True,
                clean=True
            )
            doc.close()
        except Exception:
            if os.path.exists(temp_pass1_path):
                os.remove(temp_pass1_path)

        pass1_success = os.path.exists(temp_pass1_path) and os.path.getsize(temp_pass1_path) < original_size

        if pass1_success:
            if os.path.exists(output_path):
                os.remove(output_path)
            shutil.move(temp_pass1_path, output_path)
        else:
            if os.path.exists(temp_pass1_path):
                os.remove(temp_pass1_path)
                
            try:
                with pikepdf.Pdf.open(file_path) as pdf:
                    pdf.save(
                        output_path,
                        compress_streams=True,
                        object_stream_mode=pikepdf.ObjectStreamMode.generate,
                        remove_unreferenced_resources=True
                    )
            except Exception:
                shutil.copyfile(file_path, output_path)

    try:
        await asyncio.to_thread(_do_compress)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PDF Compression failed: {str(e)}"
        )

async def create_zip_archive(file_paths: list[str], output_path: str):
    """Creates a zip archive containing all specified files."""
    with zipfile.ZipFile(output_path, 'w') as zipf:
        for file in file_paths:
            arcname = os.path.basename(file)
            zipf.write(file, arcname=arcname)

async def rotate_pdf(file_path: str, angle: int, output_path: str):
    """Rotates all pages in the PDF by a specific angle."""
    with open(file_path, "rb") as f_in:
        reader = PdfReader(f_in)
        writer = PdfWriter()
        
        angle = int(angle) % 360
        for page in reader.pages:
            page.rotate(angle)
            writer.add_page(page)
            
        with open(output_path, "wb") as f_out:
            writer.write(f_out)

async def organize_pdf(file_path: str, page_order: str, output_path: str):
    """Reorders or deletes pages."""
    with open(file_path, "rb") as f_in:
        reader = PdfReader(f_in)
        writer = PdfWriter()
        max_pages = len(reader.pages)
        
        if page_order:
            try:
                indices = [int(p.strip()) - 1 for p in page_order.split(',') if p.strip()]
                for i in indices:
                    if 0 <= i < max_pages:
                        writer.add_page(reader.pages[i])
            except ValueError:
                pass
                
        with open(output_path, "wb") as f_out:
            writer.write(f_out)

async def add_page_numbers(file_path: str, output_path: str):
    """Adds basic page numbers to the bottom center of each page."""
    with open(file_path, "rb") as f_in:
        reader = PdfReader(f_in)
        writer = PdfWriter()
        total_pages = len(reader.pages)
        
        packets = []
        for i, page in enumerate(reader.pages):
            mb = page.mediabox
            width = float(mb.width)
            height = float(mb.height)
            
            packet = io.BytesIO()
            packets.append(packet)
            
            can = canvas.Canvas(packet, pagesize=(width, height))
            can.setFont("Helvetica", 10)
            
            text = f"Page {i + 1} of {total_pages}"
            text_width = can.stringWidth(text, "Helvetica", 10)
            
            can.drawString((width - text_width) / 2.0, 30, text)
            can.save()
            packet.seek(0)
            
            stamp_pdf = PdfReader(packet)
            stamp_page = stamp_pdf.pages[0]
            
            page.merge_page(stamp_page)
            writer.add_page(page)

        with open(output_path, "wb") as f_out:
            writer.write(f_out)

async def pdf_to_jpg(file_path: str, output_zip_path: str, job_dir: str):
    """Converts a PDF to JPG images and zips them."""
    import fitz
    doc = fitz.open(file_path)
    
    with zipfile.ZipFile(output_zip_path, 'w') as zipf:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=150)
            img_path = os.path.join(job_dir, f"page_{i + 1}.jpg")
            pix.save(img_path)
            zipf.write(img_path, arcname=f"page_{i + 1}.jpg")

async def jpg_to_pdf(image_paths: list[str], output_path: str):
    """Combines multiple JPG images into a single PDF."""
    if not image_paths:
        raise HTTPException(status_code=400, detail="No images provided")
        
    images = []
    for p in image_paths:
        with Image.open(p) as img:
            img.load() # Force load into memory so the file handle can close
            images.append(img.convert("RGB"))
            
    images[0].save(output_path, save_all=True, append_images=images[1:])

async def protect_pdf(file_path: str, password: str, output_path: str):
    """Encrypts a PDF with a user-provided password."""
    with pikepdf.Pdf.open(file_path) as pdf:
        pdf.save(
            output_path, 
            encryption=pikepdf.Encryption(user=password, owner=password)
        )

async def unlock_pdf(file_path: str, password: str, output_path: str):
    """Removes the password from a PDF."""
    try:
        with pikepdf.Pdf.open(file_path, password=password) as pdf:
            pdf.save(output_path)
    except pikepdf.PasswordError:
        raise HTTPException(status_code=401, detail="Invalid password")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to unlock: {str(e)}")

async def watermark_pdf(file_path: str, watermark_text: str, output_path: str):
    """Stamps a text watermark diagonally across each page."""
    with open(file_path, "rb") as f_in:
        reader = PdfReader(f_in)
        writer = PdfWriter()
        
        packets = []
        for page in reader.pages:
            mb = page.mediabox
            width, height = float(mb.width), float(mb.height)
            
            packet = io.BytesIO()
            packets.append(packet)
            
            can = canvas.Canvas(packet, pagesize=(width, height))
            
            can.translate(width / 2.0, height / 2.0)
            can.rotate(45)
            can.setFont("Helvetica-Bold", 40)
            can.setFillColorRGB(0.5, 0.5, 0.5, alpha=0.3)
            
            can.drawCentredString(0, 0, watermark_text)
            can.save()
            packet.seek(0)
            
            stamp_page = PdfReader(packet).pages[0]
            page.merge_page(stamp_page)
            writer.add_page(page)

        with open(output_path, "wb") as f_out:
            writer.write(f_out)

async def sign_pdf(file_path: str, signature_image_path: str, output_path: str):
    """Adds a visual signature image to the bottom right of the last page."""
    with open(file_path, "rb") as f_in:
        reader = PdfReader(f_in)
        writer = PdfWriter()
        
        packets = []
        for i, page in enumerate(reader.pages):
            if i == len(reader.pages) - 1:
                mb = page.mediabox
                width, height = float(mb.width), float(mb.height)
                
                packet = io.BytesIO()
                packets.append(packet)
                
                can = canvas.Canvas(packet, pagesize=(width, height))
                
                sig_w, sig_h = 2 * inch, 1 * inch
                x = width - sig_w - 30
                y = 30
                
                can.drawImage(signature_image_path, x, y, width=sig_w, height=sig_h, preserveAspectRatio=True, mask='auto')
                can.save()
                packet.seek(0)
                
                stamp_page = PdfReader(packet).pages[0]
                page.merge_page(stamp_page)
                
            writer.add_page(page)
            
        with open(output_path, "wb") as f_out:
            writer.write(f_out)

async def pdf_to_word(file_path: str, output_path: str):
    """Converts a PDF to a Word (.docx) file using pdf2docx."""
    import asyncio
    
    def _convert():
        from pdf2docx import Converter
        cv = Converter(file_path)
        cv.convert(output_path, start=0, end=None)
        cv.close()

    try:
        await asyncio.to_thread(_convert)
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"PDF to Word conversion failed: {str(e)}")

async def office_to_pdf(file_path: str, output_dir: str):
    """Converts Word to PDF using docx2pdf (Requires Microsoft Word on Windows)."""
    import asyncio
    
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.pdf")
    
    try:
        try:
            from docx2pdf import convert
        except ImportError:
            raise Exception("docx2pdf is not installed. Please run 'pip install docx2pdf'")
            
        # docx2pdf convert is blocking, so we run it in a thread
        await asyncio.to_thread(convert, file_path, output_path)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Word to PDF conversion failed: {str(e)}. (Note: MS Word must be installed on the server)"
        )
        
    if not os.path.exists(output_path):
        raise HTTPException(status_code=500, detail="Output PDF not found after conversion")
        
    return output_path

async def excel_to_pdf(file_path: str, output_dir: str):
    """Converts Excel to PDF using comtypes (Requires Microsoft Excel on Windows)."""
    import asyncio
    
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.pdf")
    abs_file_path = os.path.abspath(file_path)
    abs_output_path = os.path.abspath(output_path)
    
    def _convert():
        import comtypes.client
        comtypes.CoInitialize()
        try:
            excel = comtypes.client.CreateObject('Excel.Application')
            excel.Visible = False
            wb = excel.Workbooks.Open(abs_file_path)
            # 0 is xlTypePDF
            wb.ExportAsFixedFormat(0, abs_output_path)
            wb.Close(False)
            excel.Quit()
        except Exception as e:
            raise Exception(f"Excel COM Error: {str(e)}")
        finally:
            comtypes.CoUninitialize()

    try:
        await asyncio.to_thread(_convert)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Excel to PDF conversion failed: {str(e)}. (Note: MS Excel must be installed on the server)"
        )
        
    if not os.path.exists(output_path):
        raise HTTPException(status_code=500, detail="Output PDF not found after conversion")
        
    return output_path

async def powerpoint_to_pdf(file_path: str, output_dir: str):
    """Converts PowerPoint to PDF using comtypes (Requires Microsoft PowerPoint on Windows)."""
    import asyncio
    
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.pdf")
    abs_file_path = os.path.abspath(file_path)
    abs_output_path = os.path.abspath(output_path)
    
    def _convert():
        import comtypes.client
        comtypes.CoInitialize()
        try:
            powerpoint = comtypes.client.CreateObject('Powerpoint.Application')
            # 32 is ppSaveAsPDF
            presentation = powerpoint.Presentations.Open(abs_file_path, WithWindow=False)
            presentation.SaveAs(abs_output_path, 32)
            presentation.Close()
            powerpoint.Quit()
        except Exception as e:
            raise Exception(f"PowerPoint COM Error: {str(e)}")
        finally:
            comtypes.CoUninitialize()

    try:
        await asyncio.to_thread(_convert)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"PowerPoint to PDF conversion failed: {str(e)}. (Note: MS PowerPoint must be installed on the server)"
        )
        
    if not os.path.exists(output_path):
        raise HTTPException(status_code=500, detail="Output PDF not found after conversion")
        
    return output_path

def _ensure_tessdata(safe_lang: str):
    import os
    import shutil
    import urllib.request
    
    local_tessdata = os.path.join(os.getcwd(), 'tessdata')
    os.makedirs(local_tessdata, exist_ok=True)
    
    base_tessdata = r'C:\Program Files\Tesseract-OCR\tessdata'
    if not os.path.exists(base_tessdata):
        base_tessdata = r'C:\Program Files (x86)\Tesseract-OCR\tessdata'
        
    if base_tessdata and os.path.exists(base_tessdata):
        if not os.path.exists(os.path.join(local_tessdata, 'eng.traineddata')):
            for f in os.listdir(base_tessdata):
                if f.endswith('.traineddata'):
                    try:
                        shutil.copy(os.path.join(base_tessdata, f), local_tessdata)
                    except Exception:
                        pass

    lang_file = os.path.join(local_tessdata, f"{safe_lang}.traineddata")
    if not os.path.exists(lang_file):
        try:
            url = f"https://github.com/tesseract-ocr/tessdata_fast/raw/main/{safe_lang}.traineddata"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(lang_file, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
        except Exception as e:
            if os.path.exists(lang_file):
                os.remove(lang_file)
            raise Exception(f"Missing language '{safe_lang}'. Auto-download failed. Please manually download '{safe_lang}.traineddata' and place it in {local_tessdata}")

    os.environ['TESSDATA_PREFIX'] = local_tessdata

async def ocr_extract_text(file_path: str, output_path: str, lang: str = 'eng'):
    """Extracts text from a PDF using OCR."""
    import asyncio
    
    def _convert():
        try:
            import pytesseract
            import os
            # Default Windows installation path
            default_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            if os.path.exists(default_path):
                pytesseract.pytesseract.tesseract_cmd = default_path
            elif os.path.exists(r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'):
                pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
        except ImportError:
            raise Exception("pytesseract is not installed. Please run 'pip install pytesseract'")
            
        # Map common full names to 3-letter codes
        safe_lang = lang.lower().strip()
        if safe_lang == 'english':
            safe_lang = 'eng'
        elif safe_lang == 'spanish':
            safe_lang = 'spa'
        elif safe_lang == 'french':
            safe_lang = 'fra'
        elif safe_lang == 'sinhala':
            safe_lang = 'sin'
            
        _ensure_tessdata(safe_lang)
            
        extracted_text = ""
        try:
            import fitz
            doc = fitz.open(file_path)
            for page_num, page in enumerate(doc):
                pix = page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = pytesseract.image_to_string(img, lang=safe_lang)
                extracted_text += f"--- Page {page_num + 1} ---\n{text}\n\n"
        except Exception as pdf_err:
            # Fallback for direct images if it's not a valid PDF or fitz fails
            try:
                img = Image.open(file_path)
                img = img.convert('RGB')
                img.format = 'PNG' # Force pytesseract to save temp file as PNG
                text = pytesseract.image_to_string(img, lang=safe_lang)
                extracted_text = text
            except Exception as img_err:
                err_msg = str(img_err)
                if "avif" in str(pdf_err).lower() or "avif" in file_path.lower():
                    err_msg += " (Hint: For AVIF support, run 'pip install pillow-avif-plugin' and restart the server)"
                raise Exception(f"Failed to open as PDF ({str(pdf_err)}) and failed as Image ({err_msg})")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(extracted_text)

    try:
        await asyncio.to_thread(_convert)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"OCR extraction failed: {str(e)}"
        )
        
    return output_path

async def ocr_make_searchable(file_path: str, output_path: str, lang: str = 'eng'):
    """Creates a searchable PDF using OCR."""
    import asyncio
    
    def _convert():
        try:
            import pytesseract
            import os
            # Default Windows installation path
            default_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            if os.path.exists(default_path):
                pytesseract.pytesseract.tesseract_cmd = default_path
            elif os.path.exists(r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'):
                pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
        except ImportError:
            raise Exception("pytesseract is not installed.")
            
        # Map common full names to 3-letter codes
        safe_lang = lang.lower().strip()
        if safe_lang == 'english':
            safe_lang = 'eng'
        elif safe_lang == 'spanish':
            safe_lang = 'spa'
        elif safe_lang == 'french':
            safe_lang = 'fra'
        elif safe_lang == 'sinhala':
            safe_lang = 'sin'
            
        _ensure_tessdata(safe_lang)
        
        writer = PdfWriter()
        import io
        import tempfile
        
        try:
            import fitz
            doc = fitz.open(file_path)
            for page in doc:
                pix = page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Save PIL image to temporary PNG file on disk
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_img:
                    tmp_img_path = tmp_img.name
                    img.save(tmp_img_path, format='PNG')
                
                try:
                    # Generate OCR PDF bytes using disk image path
                    pdf_bytes = pytesseract.image_to_pdf_or_hocr(tmp_img_path, extension='pdf', lang=safe_lang)
                    reader = PdfReader(io.BytesIO(pdf_bytes))
                    writer.add_page(reader.pages[0])
                finally:
                    if os.path.exists(tmp_img_path):
                        os.remove(tmp_img_path)
        except Exception as pdf_err:
            try:
                img = Image.open(file_path)
                img = img.convert('RGB')
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_img:
                    tmp_img_path = tmp_img.name
                    img.save(tmp_img_path, format='PNG')
                try:
                    pdf_bytes = pytesseract.image_to_pdf_or_hocr(tmp_img_path, extension='pdf', lang=safe_lang)
                    reader = PdfReader(io.BytesIO(pdf_bytes))
                    writer.add_page(reader.pages[0])
                finally:
                    if os.path.exists(tmp_img_path):
                        os.remove(tmp_img_path)
            except Exception as img_err:
                err_msg = str(img_err)
                raise Exception(f"Failed to open as PDF ({str(pdf_err)}) and failed as Image ({err_msg})")
            
        with open(output_path, "wb") as f_out:
            writer.write(f_out)

    try:
        await asyncio.to_thread(_convert)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Searchable OCR failed: {str(e)}. (Ensure Tesseract-OCR is installed on C:\\Program Files\\Tesseract-OCR\\tesseract.exe)"
        )
        
    return output_path


logger = logging.getLogger(__name__)


def _merge_word_documents_docxcompose(file_paths: list[str], output_path: str) -> str:
    """
    Enhanced cross-platform Word document merge using python-docx and docxcompose.
    Explicitly preserves headers, footers, images, and tables by unlinking headers/footers
    and inserting clean Section Breaks between appended documents.
    """
    if Document is None or Composer is None or WD_SECTION is None:
        raise HTTPException(
            status_code=500,
            detail="Required packages (python-docx, docxcompose) are missing on the server."
        )

    # Filter out non-existent files
    valid_paths = [p for p in file_paths if os.path.exists(p)]
    if not valid_paths:
        raise HTTPException(status_code=400, detail="No valid Word documents found to merge.")

    master_doc = None
    master_index = -1

    # Find first valid document to serve as composer master
    for idx, path in enumerate(valid_paths):
        file_name = os.path.basename(path)
        try:
            master_doc = Document(path)
            master_index = idx
            logger.info(f"Initialized docxcompose master document: '{file_name}'")
            break
        except Exception as e:
            logger.error(f"Failed to parse initial master document '{file_name}': {str(e)}\n{traceback.format_exc()}")

    if master_doc is None:
        raise HTTPException(status_code=400, detail="All provided Word documents failed to parse.")

    composer = Composer(master_doc)
    successful_count = 1

    for idx in range(master_index + 1, len(valid_paths)):
        file_path = valid_paths[idx]
        file_name = os.path.basename(file_path)

        try:
            doc = Document(file_path)

            # Unlink headers and footers to avoid bleeding into/overwriting preceding sections
            for section in doc.sections:
                section.header.is_linked_to_previous = False
                section.footer.is_linked_to_previous = False

            # Add a clean section break (Next Page) so layouts, margins, and headers do not collide
            master_doc.add_section(WD_SECTION.NEW_PAGE)

            # Append the parsed document
            composer.append(doc)
            successful_count += 1
            logger.info(f"Successfully appended document '{file_name}' ({successful_count}/{len(valid_paths)})")
            
            # Aggressively collect garbage to free up memory from large parsed documents
            import gc
            gc.collect()

        except Exception as e:
            # Per-file exception handling: Log exact filename and stack trace without corrupting the batch
            logger.error(
                f"Error processing file '{file_name}' during docxcompose merge: {str(e)}\n{traceback.format_exc()}"
            )
            continue

    try:
        composer.save(output_path)
        logger.info(f"Saved docxcompose merged output to '{output_path}' ({successful_count} files merged)")
    except Exception as e:
        logger.error(f"Failed to save final merged document: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to save merged Word document: {str(e)}")

    return output_path


def _merge_word_documents_win32(file_paths: list[str], output_path: str) -> str:
    """
    Windows-Native Word document merge using win32com.client (MS Word COM Automation).
    Uses Word's native engine (0% data loss) for complex formatting, headers/footers, and tables.
    Includes strict try-finally cleanup logic to ensure no hidden Word processes remain in Task Manager.
    """
    if win32com is None or pythoncom is None:
        raise HTTPException(
            status_code=500,
            detail="pywin32 (win32com) is not installed on the server for Windows COM automation."
        )

    valid_paths = [os.path.abspath(p) for p in file_paths if os.path.exists(p)]
    if not valid_paths:
        raise HTTPException(status_code=400, detail="No valid Word documents found for win32 merge.")

    abs_output_path = os.path.abspath(output_path)

    # Initialize COM library for current thread
    pythoncom.CoInitialize()

    word = None
    master_doc = None
    successful_count = 0

    try:
        # Launch MS Word process in background
        word = win32com.client.DispatchEx("Word.Application")
        # STRICT ANTI-FREEZE: Disable alerts, visibility, and screen updating immediately
        word.Visible = False
        word.DisplayAlerts = 0  # 0 = wdAlertsNone (suppress popups, warnings, and dialogs)
        try:
            word.ScreenUpdating = False
        except Exception:
            pass

        # Open the first document as master without interactive prompts
        master_doc = word.Documents.Open(
            FileName=valid_paths[0],
            ConfirmConversions=False,
            ReadOnly=False,
            AddToRecentFiles=False
        )
        successful_count = 1
        selection = word.Selection

        for file_path in valid_paths[1:]:
            file_name = os.path.basename(file_path)
            try:
                # Move cursor to the end of the current document (6 = wdStory)
                selection.EndKey(Unit=6)

                # Insert Next Page Section Break (2 = wdSectionBreakNextPage)
                selection.InsertBreak(Type=2)

                # Insert document natively using MS Word's rendering engine
                selection.InsertFile(FileName=file_path, ConfirmConversions=False)
                successful_count += 1
                logger.info(f"Win32 COM appended '{file_name}' ({successful_count}/{len(valid_paths)})")

            except Exception as file_err:
                logger.error(
                    f"Win32 COM failed to insert '{file_name}': {str(file_err)}\n{traceback.format_exc()}"
                )
                continue

        # Save as docx (16 = wdFormatXMLDocument)
        master_doc.SaveAs2(FileName=abs_output_path, FileFormat=16)
        logger.info(f"Saved Win32 COM merged document to '{abs_output_path}' ({successful_count} files merged)")

    except Exception as e:
        logger.error(f"Win32 COM Word merge error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Windows COM Word merge failed: {str(e)}")

    finally:
        # Guaranteed process cleanup: ensure master_doc and Word application quit cleanly
        if master_doc is not None:
            try:
                master_doc.Close(0)  # 0 = wdDoNotSaveChanges
            except Exception as close_err:
                logger.warning(f"Error closing master document: {str(close_err)}")

        if word is not None:
            try:
                word.Quit(0)  # 0 = wdDoNotSaveChanges
            except Exception as quit_err:
                logger.warning(f"Error quitting MS Word application: {str(quit_err)}")

        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

    return output_path


async def merge_word_documents_docxcompose(file_paths: list[str], output_path: str) -> str:
    """Async wrapper for docxcompose Word document merging."""
    return await asyncio.to_thread(_merge_word_documents_docxcompose, file_paths, output_path)


async def merge_word_documents_win32(file_paths: list[str], output_path: str) -> str:
    """Async wrapper for Windows COM Word document merging."""
    return await asyncio.to_thread(_merge_word_documents_win32, file_paths, output_path)


async def merge_word_documents(file_paths: list[str], output_path: str, prefer_win32: bool = True) -> str:
    """
    Primary endpoint helper to merge Word documents (.docx).
    Attempts Windows COM Automation first on Windows hosts (0% data loss), falling back
    to enhanced docxcompose logic if Win32 COM is unavailable or fails.
    """
    if not file_paths:
        raise HTTPException(status_code=400, detail="No Word documents provided for merging.")

    total_size = sum(os.path.getsize(p) for p in file_paths if os.path.exists(p))
    # If total size exceeds 10MB, skip COM automation because it tends to hang
    if total_size > 10 * 1024 * 1024:
        logger.info(f"Total Word documents size ({total_size / 1024 / 1024:.2f} MB) exceeds 10MB limit. Skipping Win32 COM automation.")
        prefer_win32 = False

    if prefer_win32 and os.name == 'nt':
        logger.info("Attempting Word document merge via Windows COM automation...")
        try:
            # Wrap COM merge in a strict timeout (60 seconds) to prevent infinite hangs
            return await asyncio.wait_for(
                merge_word_documents_win32(file_paths, output_path), 
                timeout=60.0
            )
        except asyncio.TimeoutError:
            logger.warning("Win32 COM merge timed out. Falling back to docxcompose engine.")
        except Exception as e:
            logger.warning(f"Win32 COM merge encountered an issue, falling back to docxcompose engine: {str(e)}")

    # Cross-platform / fallback docxcompose engine
    logger.info("Merging Word documents via enhanced docxcompose engine...")
    return await merge_word_documents_docxcompose(file_paths, output_path)


def _merge_powerpoint_presentations_win32(file_paths: list[str], output_path: str) -> str:
    """Windows-Native PowerPoint merge using win32com.client."""
    if win32com is None or pythoncom is None:
        raise HTTPException(
            status_code=500,
            detail="pywin32 (win32com) is not installed on the server for Windows COM automation."
        )

    valid_paths = [os.path.abspath(p) for p in file_paths if os.path.exists(p)]
    if not valid_paths:
        raise HTTPException(status_code=400, detail="No valid PowerPoint documents found.")

    abs_output_path = os.path.abspath(output_path)
    pythoncom.CoInitialize()

    ppt = None
    master_pres = None
    successful_count = 0

    try:
        ppt = win32com.client.DispatchEx("PowerPoint.Application")
        
        master_pres = ppt.Presentations.Open(valid_paths[0], WithWindow=False)
        successful_count = 1

        for file_path in valid_paths[1:]:
            try:
                num_slides = master_pres.Slides.Count
                master_pres.Slides.InsertFromFile(file_path, num_slides)
                successful_count += 1
                logger.info(f"Win32 COM appended PPTX '{os.path.basename(file_path)}'")
            except Exception as file_err:
                logger.error(f"Win32 COM failed to insert PPTX '{os.path.basename(file_path)}': {str(file_err)}")
                continue
        
        master_pres.SaveAs(abs_output_path, FileFormat=24)  # 24 = ppSaveAsOpenXMLPresentation (.pptx)
        logger.info(f"Saved merged PPTX to '{abs_output_path}'")
    except Exception as e:
        logger.error(f"Win32 COM PPTX merge error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Windows COM PPTX merge failed: {str(e)}")
    finally:
        if master_pres is not None:
            try:
                master_pres.Close()
            except Exception:
                pass
        if ppt is not None:
            try:
                ppt.Quit()
            except Exception:
                pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

    return output_path

async def merge_powerpoint_presentations(file_paths: list[str], output_path: str) -> str:
    """Async wrapper for PowerPoint merging."""
    if os.name != 'nt':
        raise HTTPException(status_code=500, detail="PowerPoint merging is only supported on Windows servers.")
    return await asyncio.to_thread(_merge_powerpoint_presentations_win32, file_paths, output_path)

def _merge_excel_workbooks_win32(file_paths: list[str], output_path: str) -> str:
    """Windows-Native Excel merge using win32com.client."""
    if win32com is None or pythoncom is None:
        raise HTTPException(
            status_code=500,
            detail="pywin32 (win32com) is not installed on the server for Windows COM automation."
        )

    valid_paths = [os.path.abspath(p) for p in file_paths if os.path.exists(p)]
    if not valid_paths:
        raise HTTPException(status_code=400, detail="No valid Excel documents found.")

    abs_output_path = os.path.abspath(output_path)
    pythoncom.CoInitialize()

    excel = None
    master_wb = None
    successful_count = 0

    try:
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        
        master_wb = excel.Workbooks.Open(valid_paths[0])
        successful_count = 1

        for file_path in valid_paths[1:]:
            try:
                wb = excel.Workbooks.Open(file_path)
                for sheet in wb.Sheets:
                    sheet.Copy(After=master_wb.Sheets(master_wb.Sheets.Count))
                wb.Close(SaveChanges=False)
                successful_count += 1
                logger.info(f"Win32 COM appended XLSX '{os.path.basename(file_path)}'")
            except Exception as file_err:
                logger.error(f"Win32 COM failed to insert XLSX '{os.path.basename(file_path)}': {str(file_err)}")
                continue
        
        master_wb.SaveAs(abs_output_path, FileFormat=51)
        logger.info(f"Saved merged XLSX to '{abs_output_path}'")
    except Exception as e:
        logger.error(f"Win32 COM XLSX merge error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Windows COM XLSX merge failed: {str(e)}")
    finally:
        if master_wb is not None:
            try:
                master_wb.Close(SaveChanges=False)
            except Exception:
                pass
        if excel is not None:
            try:
                excel.Quit()
            except Exception:
                pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

    return output_path

async def merge_excel_workbooks(file_paths: list[str], output_path: str) -> str:
    """Async wrapper for Excel merging."""
    if os.name != 'nt':
        raise HTTPException(status_code=500, detail="Excel merging is only supported on Windows servers.")
    return await asyncio.to_thread(_merge_excel_workbooks_win32, file_paths, output_path)

