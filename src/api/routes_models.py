from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from botocore.exceptions import ClientError
from src.services.auth import verify_api_key
from src.services.rate_limit import rate_limiter, enforce_rate_limit
from src.services.s3_service import (
    upload_file_to_s3,
    get_s3_object_checksum,
    generate_presigned_download_url,
    write_manifest,
    read_manifest,
)
import os, tempfile, hashlib, zipfile, logging, time
from datetime import datetime

logger = logging.getLogger("trustworthy-registry")

router = APIRouter(
    dependencies=[Depends(enforce_rate_limit)]
)

# Limits
ALLOWED_MIME = {"application/zip", "application/x-zip-compressed"}
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 50 * 1024 * 1024))  # 50MB


def compute_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_zip_safely(zip_path: str):
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for entry in z.namelist():

                # Prevent traversal attacks
                if entry.startswith("/") or ".." in entry.replace("\\", "/"):
                    raise HTTPException(status_code=400, detail="Invalid file paths in ZIP")

                # Block risky file types
                if entry.lower().endswith((".exe", ".dll", ".sh", ".py", ".bat")):
                    raise HTTPException(status_code=400, detail="Archive contains disallowed types")

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Not a valid ZIP")

@router.get("/download/{filename}")
def download_model(filename: str, user_info: dict = Depends(verify_api_key)):
    user_id = user_info.get("user", "unknown")
    s3_key = f"models/{filename}"
    # read manifest
    manifest = read_manifest(s3_key)
    if not manifest:
        logger.warning(f"download requested for {s3_key} but manifest missing")
        raise HTTPException(status_code=404, detail="Model metadata missing or file not found")
    # verify checksum exists
    stored_checksum = manifest.get("checksum")
    if not stored_checksum:
        raise HTTPException(status_code=404, detail="Model missing checksum")
    # Optionally compare the metadata checksum with head_object metadata
    head_chk = get_s3_object_checksum(s3_key)
    if head_chk and head_chk != stored_checksum:
        logger.error(f"Checksum mismatch for {s3_key}: manifest={stored_checksum} head={head_chk}")
        raise HTTPException(status_code=500, detail="Integrity check failed")

    presigned = generate_presigned_download_url(s3_key, expires_in=300)
    if not presigned:
        raise HTTPException(status_code=500, detail="Failed to generate presigned URL")

    logger.info(f"download event: user={user_id} filename={filename}")
    return JSONResponse({"download_url": presigned, "checksum": stored_checksum})

@router.post("/upload")
async def upload_model(
    file: UploadFile = File(...),
    user_info: dict = Depends(verify_api_key)
):
    """Upload a secure model ZIP file + generate manifest."""

    # Extract authenticated user
    user_id = user_info.get("user", "unknown")

    # Apply rate limiting
    if not rate_limiter.allow(user_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Validate MIME
    if (
        file.content_type not in ALLOWED_MIME
        and not file.filename.lower().endswith(".zip")
    ):
        raise HTTPException(status_code=400, detail="Only ZIP files allowed")

    # Save to temp
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
        contents = await file.read()

        # Validate size
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Upload exceeds size limit")

        tmp.write(contents)
        tmp.flush()

    # ZIP safety check
    validate_zip_safely(tmp_path)

    # Compute checksum
    checksum = compute_sha256(tmp_path)

    # Upload to S3
    s3_key = f"models/{file.filename}"
    upload_file_to_s3(tmp_path, s3_key, checksum=checksum)

    # Write manifest
    manifest = {
        "uploader": user_id,
        "checksum": checksum,
        "filename": file.filename,
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
        "notes": "manifest auto-generated",
    }
    write_manifest(s3_key, manifest)

    # Cleanup temp file
    try:
        os.remove(tmp_path)
    except Exception:
        pass

    return {
        "success": True,
        "filename": file.filename,
        "checksum": checksum,
        "manifest": manifest,
    }
