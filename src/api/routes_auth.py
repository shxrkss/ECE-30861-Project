# src/api/routes_auth.py
from fastapi import APIRouter, HTTPException
from src.models.artifacts import AuthenticationRequest

router = APIRouter(tags=["auth"])


@router.put("/authenticate")
def create_auth_token(_req: AuthenticationRequest):
    """
    Spec: If you don't implement the described auth scheme,
    this endpoint MUST return HTTP 501 and X-Authorization should
    be ignored by other endpoints (we still enforce presence though).
    """
    raise HTTPException(status_code=501, detail="Authentication not implemented")
