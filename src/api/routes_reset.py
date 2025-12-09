# src/api/routes_reset.py
from fastapi import APIRouter, Header, Depends, HTTPException
from src.services.artifact_store import reset_store

router = APIRouter(tags=["admin"])


def require_auth(x_authorization: str = Header(..., alias="X-Authorization")):
    if not x_authorization:
        raise HTTPException(status_code=403, detail="Authentication failed")
    return x_authorization


@router.delete("/reset")
def registry_reset(_token: str = Depends(require_auth)):
    """
    Reset the registry to a system default state.

    BASELINE requirement:
    - Return HTTP 200 on success.
    - 403 on missing/invalid auth.
    """
    reset_store()
    # If you also want to clear S3 contents, you can call delete_prefix("models/")
    # from src.services.s3_service here.
    return {"status": "Registry is reset."}
