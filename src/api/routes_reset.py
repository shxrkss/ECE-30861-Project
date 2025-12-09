# src/api/routes_reset.py
from fastapi import APIRouter, Header, Depends, HTTPException
from src.services.artifact_store import reset_store

router = APIRouter(tags=["admin"])


def require_auth(x_authorization: str = Header(..., alias="X-Authorization")):
    return x_authorization


@router.delete("/reset")
def registry_reset(_token: str = Depends(require_auth)):
    reset_store()
    return {"status": "Registry is reset."}
