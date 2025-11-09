from src.aws_utils import upload_file_to_s3, download_file_from_s3
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from botocore.exceptions import ClientError
from src.aws_utils import s3_client, S3_BUCKET
import os
import tempfile
import logging

router = APIRouter()

@router.post("/upload") 
async def upload_model(file: UploadFile = File(...)):
    """Upload zipped model file to S3."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(await file.read())
        tmp.flush()
        success = upload_file_to_s3(tmp.name, f"models/{file.filename}")
    return {"success": success, "filename": file.filename}

@router.get("/download/{filename}")
def download_model(filename: str):
    """Download a model file from S3."""
    local_dir = tempfile.gettempdir()
    local_path = os.path.join(local_dir, filename)
    s3_key = f"models/{filename}"

    try:
        # Try to download file from S3
        s3_client.download_file(S3_BUCKET, s3_key, local_path)
    except ClientError as e:
        # Handle AWS errors cleanly
        logging.error(f"Download failed: {e}")
        if e.response["Error"]["Code"] == "404":
            raise HTTPException(status_code=404, detail="File not found in S3")
        else:
            raise HTTPException(status_code=500, detail=str(e))

    # Check local file exists
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="Downloaded file not found on server")

    # Serve the file back to the client
    return FileResponse(
        path=local_path,
        media_type="application/octet-stream",
        filename=filename
    )
