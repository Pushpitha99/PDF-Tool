import os
import uuid
import shutil
import tempfile
from fastapi import UploadFile

class TempFileManager:
    def __init__(self, base_temp_dir: str = None):
        """
        Initializes the TempFileManager with a unique job ID and a dedicated directory.
        """
        self.base_temp_dir = base_temp_dir or os.path.join(tempfile.gettempdir(), "pdf_microservice_temp")
        self.job_id = str(uuid.uuid4())
        self.job_dir = os.path.join(self.base_temp_dir, self.job_id)
        os.makedirs(self.job_dir, exist_ok=True)

    async def save_upload_file(self, upload_file: UploadFile) -> str:
        """
        Saves a FastAPI UploadFile to the temporary job directory.
        Raises an error if the file is empty.
        """
        file_path = os.path.join(self.job_dir, upload_file.filename)
        import shutil
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
            
        size = os.path.getsize(file_path)
        if size == 0:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"File '{upload_file.filename}' is empty.")
            
        return file_path

    def get_job_id(self) -> str:
        return self.job_id
        
    def get_job_dir(self) -> str:
        return self.job_dir

    def cleanup(self):
        """
        Removes the entire job directory and all its contents.
        """
        if os.path.exists(self.job_dir):
            shutil.rmtree(self.job_dir, ignore_errors=True)

async def get_temp_file_manager():
    """
    FastAPI Dependency that provides a TempFileManager instance per request.
    Automatically cleans up the temporary files after the response is sent.
    """
    manager = TempFileManager()
    try:
        yield manager
    finally:
        manager.cleanup()
