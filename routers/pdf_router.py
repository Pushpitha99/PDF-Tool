import os
import logging
import traceback
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from utils.temp_file_manager import TempFileManager, get_temp_file_manager
from services import pdf_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/merge")
async def merge_pdf_endpoint(
    files: List[UploadFile] = File(...),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    saved_file_paths = []
    for file in files:
        path = await temp_manager.save_upload_file(file)
        saved_file_paths.append(path)
        
    output_path = os.path.join(temp_manager.get_job_dir(), "merged.pdf")
    await pdf_service.merge_pdfs(saved_file_paths, output_path)
    
    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename="merged.pdf"
    )

@router.post("/split")
async def split_pdf_endpoint(
    file: UploadFile = File(...),
    page_ranges: str = Form(..., description="e.g. 1-3,5,7-9"),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    saved_file_path = await temp_manager.save_upload_file(file)
    output_path = os.path.join(temp_manager.get_job_dir(), "split.pdf")
    
    await pdf_service.split_pdf(saved_file_path, page_ranges, output_path)
    
    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename="split.pdf"
    )

@router.post("/compress")
async def compress_pdf_endpoint(
    files: List[UploadFile] = File(None),
    file: UploadFile = File(None),
    compression_level: str = Form("recommended"),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    upload_files = files if files else ([file] if file else [])
    if not upload_files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    if len(upload_files) == 1:
        saved_file_path = await temp_manager.save_upload_file(upload_files[0])
        output_path = os.path.join(temp_manager.get_job_dir(), "compressed.pdf")
        await pdf_service.compress_pdf(saved_file_path, output_path, compression_level)
        return FileResponse(
            output_path, 
            media_type="application/pdf", 
            filename="compressed.pdf"
        )
    else:
        compressed_paths = []
        for f in upload_files:
            saved_path = await temp_manager.save_upload_file(f)
            out_filename = f"compressed_{f.filename if f.filename else 'file.pdf'}"
            out_path = os.path.join(temp_manager.get_job_dir(), out_filename)
            await pdf_service.compress_pdf(saved_path, out_path, compression_level)
            compressed_paths.append(out_path)
        
        zip_path = os.path.join(temp_manager.get_job_dir(), "compressed_pdfs.zip")
        await pdf_service.create_zip_archive(compressed_paths, zip_path)
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename="compressed_pdfs.zip"
        )

@router.post("/rotate")
async def rotate_pdf_endpoint(
    file: UploadFile = File(...),
    angle: int = Form(..., description="Rotation angle: 90, 180, 270"),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    saved_file_path = await temp_manager.save_upload_file(file)
    output_path = os.path.join(temp_manager.get_job_dir(), "rotated.pdf")
    
    await pdf_service.rotate_pdf(saved_file_path, angle, output_path)
    
    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename="rotated.pdf"
    )

@router.post("/organize")
async def organize_pdf_endpoint(
    file: UploadFile = File(...),
    page_order: str = Form(..., description="e.g. 3,1,2"),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    saved_file_path = await temp_manager.save_upload_file(file)
    output_path = os.path.join(temp_manager.get_job_dir(), "organized.pdf")
    
    await pdf_service.organize_pdf(saved_file_path, page_order, output_path)
    
    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename="organized.pdf"
    )

@router.post("/add-page-numbers")
async def add_page_numbers_endpoint(
    file: UploadFile = File(...),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    saved_file_path = await temp_manager.save_upload_file(file)
    output_path = os.path.join(temp_manager.get_job_dir(), "numbered.pdf")
    
    await pdf_service.add_page_numbers(saved_file_path, output_path)
    
    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename="numbered.pdf"
    )

@router.post("/pdf-to-jpg")
async def pdf_to_jpg_endpoint(
    file: UploadFile = File(...),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    saved_file_path = await temp_manager.save_upload_file(file)
    output_zip_path = os.path.join(temp_manager.get_job_dir(), "images.zip")
    
    await pdf_service.pdf_to_jpg(saved_file_path, output_zip_path, temp_manager.get_job_dir())
    
    return FileResponse(
        output_zip_path, 
        media_type="application/zip", 
        filename="images.zip"
    )

@router.post("/jpg-to-pdf")
async def jpg_to_pdf_endpoint(
    files: List[UploadFile] = File(...),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    saved_file_paths = []
    for file in files:
        path = await temp_manager.save_upload_file(file)
        saved_file_paths.append(path)
        
    output_path = os.path.join(temp_manager.get_job_dir(), "images_combined.pdf")
    await pdf_service.jpg_to_pdf(saved_file_paths, output_path)
    
    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename="images_combined.pdf"
    )

@router.post("/protect")
async def protect_pdf_endpoint(
    file: UploadFile = File(...),
    password: str = Form(...),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    saved_file_path = await temp_manager.save_upload_file(file)
    output_path = os.path.join(temp_manager.get_job_dir(), "protected.pdf")
    
    await pdf_service.protect_pdf(saved_file_path, password, output_path)
    
    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename="protected.pdf"
    )

@router.post("/unlock")
async def unlock_pdf_endpoint(
    file: UploadFile = File(...),
    password: str = Form(...),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    saved_file_path = await temp_manager.save_upload_file(file)
    output_path = os.path.join(temp_manager.get_job_dir(), "unlocked.pdf")
    
    await pdf_service.unlock_pdf(saved_file_path, password, output_path)
    
    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename="unlocked.pdf"
    )

@router.post("/watermark")
async def watermark_pdf_endpoint(
    file: UploadFile = File(...),
    watermark_text: str = Form(...),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    saved_file_path = await temp_manager.save_upload_file(file)
    output_path = os.path.join(temp_manager.get_job_dir(), "watermarked.pdf")
    
    await pdf_service.watermark_pdf(saved_file_path, watermark_text, output_path)
    
    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename="watermarked.pdf"
    )

@router.post("/sign")
async def sign_pdf_endpoint(
    file: UploadFile = File(...),
    signature_image: UploadFile = File(...),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    saved_file_path = await temp_manager.save_upload_file(file)
    saved_sig_path = await temp_manager.save_upload_file(signature_image)
    output_path = os.path.join(temp_manager.get_job_dir(), "signed.pdf")
    
    await pdf_service.sign_pdf(saved_file_path, saved_sig_path, output_path)
    
    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename="signed.pdf"
    )

@router.post("/pdf-to-word")
async def pdf_to_word_endpoint(
    file: UploadFile = File(...),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    saved_file_path = await temp_manager.save_upload_file(file)
    output_path = os.path.join(temp_manager.get_job_dir(), "converted.docx")
    
    await pdf_service.pdf_to_word(saved_file_path, output_path)
    
    return FileResponse(
        output_path, 
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
        filename="converted.docx"
    )

@router.post("/word-to-pdf")
async def word_to_pdf_endpoint(
    file: UploadFile = File(...),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    saved_file_path = await temp_manager.save_upload_file(file)
    output_path = await pdf_service.office_to_pdf(saved_file_path, temp_manager.get_job_dir())
    
    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename="from_word.pdf"
    )

@router.post("/excel-to-pdf")
async def excel_to_pdf_endpoint(
    file: UploadFile = File(...),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    saved_file_path = await temp_manager.save_upload_file(file)
    output_path = await pdf_service.excel_to_pdf(saved_file_path, temp_manager.get_job_dir())
    
    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename="from_excel.pdf"
    )

@router.post("/powerpoint-to-pdf")
async def powerpoint_to_pdf_endpoint(
    file: UploadFile = File(...),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    saved_file_path = await temp_manager.save_upload_file(file)
    output_path = await pdf_service.powerpoint_to_pdf(saved_file_path, temp_manager.get_job_dir())
    
    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename="from_powerpoint.pdf"
    )

@router.post("/ocr-text")
async def ocr_text_endpoint(
    file: UploadFile = File(...),
    language: str = Form("eng"),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    saved_file_path = await temp_manager.save_upload_file(file)
    output_path = os.path.join(temp_manager.get_job_dir(), "extracted.txt")
    
    await pdf_service.ocr_extract_text(saved_file_path, output_path, lang=language)
    
    return FileResponse(
        output_path, 
        media_type="text/plain", 
        filename="extracted_text.txt"
    )

@router.post("/ocr-pdf")
async def ocr_pdf_endpoint(
    file: UploadFile = File(...),
    language: str = Form("eng"),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    saved_file_path = await temp_manager.save_upload_file(file)
    output_path = os.path.join(temp_manager.get_job_dir(), "searchable.pdf")
    
    await pdf_service.ocr_make_searchable(saved_file_path, output_path, lang=language)
    
    return FileResponse(
        output_path, 
        media_type="application/pdf", 
        filename="searchable.pdf"
    )

@router.post("/merge-word")
async def merge_word_endpoint(
    files: List[UploadFile] = File(...),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    try:
        if not files or len(files) == 0:
            raise HTTPException(status_code=400, detail="No Word files uploaded for merging.")

        saved_file_paths = []
        for file in files:
            path = await temp_manager.save_upload_file(file)
            saved_file_paths.append(path)
            
        output_path = os.path.join(temp_manager.get_job_dir(), "merged_document.docx")
        await pdf_service.merge_word_documents(saved_file_paths, output_path)
        
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Merged Word document was not generated.")

        return FileResponse(
            output_path, 
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
            filename="merged_document.docx"
        )
    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"Word document merge failed: {str(e)}"
        logger.error(f"{error_detail}\n{traceback.format_exc()}")
        print(f"[ERROR] {error_detail}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)


@router.post("/merge-powerpoint")
async def merge_powerpoint_endpoint(
    files: List[UploadFile] = File(...),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    try:
        if not files or len(files) == 0:
            raise HTTPException(status_code=400, detail="No PowerPoint files uploaded for merging.")

        saved_file_paths = []
        for file in files:
            path = await temp_manager.save_upload_file(file)
            saved_file_paths.append(path)
            
        output_path = os.path.join(temp_manager.get_job_dir(), "merged_presentation.pptx")
        await pdf_service.merge_powerpoint_presentations(saved_file_paths, output_path)
        
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Merged PowerPoint presentation was not generated.")

        return FileResponse(
            output_path, 
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", 
            filename="merged_presentation.pptx"
        )
    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"PowerPoint presentation merge failed: {str(e)}"
        logger.error(f"{error_detail}\n{traceback.format_exc()}")
        print(f"[ERROR] {error_detail}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)


@router.post("/merge-excel")
async def merge_excel_endpoint(
    files: List[UploadFile] = File(...),
    temp_manager: TempFileManager = Depends(get_temp_file_manager)
):
    try:
        if not files or len(files) == 0:
            raise HTTPException(status_code=400, detail="No Excel files uploaded for merging.")

        saved_file_paths = []
        for file in files:
            path = await temp_manager.save_upload_file(file)
            saved_file_paths.append(path)
            
        output_path = os.path.join(temp_manager.get_job_dir(), "merged_workbook.xlsx")
        await pdf_service.merge_excel_workbooks(saved_file_paths, output_path)
        
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Merged Excel workbook was not generated.")

        return FileResponse(
            output_path, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
            filename="merged_workbook.xlsx"
        )
    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"Excel workbook merge failed: {str(e)}"
        logger.error(f"{error_detail}\n{traceback.format_exc()}")
        print(f"[ERROR] {error_detail}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)
