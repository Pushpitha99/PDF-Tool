import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Positive Test: Ensures service health endpoint returns 200 OK."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_merge_pdfs_success(client, valid_pdf_1, valid_pdf_2):
    """Positive Test: Merges two valid in-memory PDFs and asserts 200 OK with PDF MIME type."""
    files = [
        ("files", (valid_pdf_1[0], valid_pdf_1[1], valid_pdf_1[2])),
        ("files", (valid_pdf_2[0], valid_pdf_2[1], valid_pdf_2[2]))
    ]
    response = await client.post("/api/v1/pdf/merge", files=files)
    
    assert response.status_code == 200
    assert "application/pdf" in response.headers.get("content-type", "")
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_merge_word_success(client, valid_docx_1, valid_docx_2):
    """Positive Test: Merges two valid in-memory .docx files and asserts 200 OK with DOCX MIME type."""
    files = [
        ("files", (valid_docx_1[0], valid_docx_1[1], valid_docx_1[2])),
        ("files", (valid_docx_2[0], valid_docx_2[1], valid_docx_2[2]))
    ]
    response = await client.post("/api/v1/pdf/merge-word", files=files)
    
    assert response.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in response.headers.get("content-type", "")
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_split_pdf_success(client, valid_pdf_1):
    """Positive Test: Splits a PDF document and asserts 200 OK."""
    files = {"file": (valid_pdf_1[0], valid_pdf_1[1], valid_pdf_1[2])}
    response = await client.post("/api/v1/pdf/split", files=files)
    
    assert response.status_code == 200
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_compress_pdf_success(client, valid_pdf_1):
    """Positive Test: Compresses a PDF document with medium compression level."""
    files = {"file": (valid_pdf_1[0], valid_pdf_1[1], valid_pdf_1[2])}
    data = {"compression_level": "medium"}
    response = await client.post("/api/v1/pdf/compress", files=files, data=data)
    
    assert response.status_code == 200
    assert "application/pdf" in response.headers.get("content-type", "")
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_watermark_pdf_success(client, valid_pdf_1):
    """Positive Test: Applies a text watermark to a PDF document."""
    files = {"file": (valid_pdf_1[0], valid_pdf_1[1], valid_pdf_1[2])}
    data = {"watermark_text": "CONFIDENTIAL SAMPLE"}
    response = await client.post("/api/v1/pdf/watermark", files=files, data=data)
    
    assert response.status_code == 200
    assert "application/pdf" in response.headers.get("content-type", "")
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_protect_pdf_success(client, valid_pdf_1):
    """Positive Test: Encrypts a PDF document with password protection."""
    files = {"file": (valid_pdf_1[0], valid_pdf_1[1], valid_pdf_1[2])}
    data = {"password": "testsecretpassword123"}
    response = await client.post("/api/v1/pdf/protect", files=files, data=data)
    
    assert response.status_code == 200
    assert "application/pdf" in response.headers.get("content-type", "")
    assert len(response.content) > 0


# ==========================================
# NEGATIVE AND EDGE-CASE TESTS
# ==========================================

@pytest.mark.asyncio
async def test_merge_pdfs_corrupted_file(client, corrupted_file, valid_pdf_1):
    """Negative Test: Uploading a corrupted file disguised as PDF returns 400 Bad Request without server crash."""
    files = [
        ("files", (corrupted_file[0], corrupted_file[1], corrupted_file[2])),
        ("files", (valid_pdf_1[0], valid_pdf_1[1], valid_pdf_1[2]))
    ]
    response = await client.post("/api/v1/pdf/merge", files=files)
    
    assert response.status_code in [400, 422]
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_merge_pdfs_empty_file(client, empty_file):
    """Negative Test: Uploading a 0-byte empty file returns 400 or 422 error."""
    files = [("files", (empty_file[0], empty_file[1], empty_file[2]))]
    response = await client.post("/api/v1/pdf/merge", files=files)
    
    assert response.status_code in [400, 422]
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_merge_word_invalid_extension(client, valid_pdf_1, valid_pdf_2):
    """Negative Test: Passing .pdf files to Word merge endpoint returns 400 Bad Request."""
    files = [
        ("files", (valid_pdf_1[0], valid_pdf_1[1], valid_pdf_1[2])),
        ("files", (valid_pdf_2[0], valid_pdf_2[1], valid_pdf_2[2]))
    ]
    response = await client.post("/api/v1/pdf/merge-word", files=files)
    
    assert response.status_code in [400, 422]
    data = response.json()
    assert "detail" in data
