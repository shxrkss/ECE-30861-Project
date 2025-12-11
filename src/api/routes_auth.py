# src/api/routes_auth.py
from fastapi import APIRouter, HTTPException
from src.models.artifacts import AuthenticationRequest

router = APIRouter(tags=["auth"])


@router.put("/authenticate")
def create_auth_token(_req: AuthenticationRequest):
    """
    We are NOT implementing access-control track.
    Per spec: return 501 and ignore X-Authorization on other endpoints.
    """
    raise HTTPException(status_code=501, detail="Authentication not implemented")
