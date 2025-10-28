from fastapi import APIRouter, UploadFile, File
from src.aws_utils import upload_file_to_s3
import tempfile

router = APIRouter()

@router.post("/upload")
async def upload_model(file: UploadFile = File(...)):
    """Upload zipped model file to S3."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(await file.read())
        tmp.flush()
        success = upload_file_to_s3(tmp.name, f"models/{file.filename}")
    return {"success": success, "filename": file.filename}