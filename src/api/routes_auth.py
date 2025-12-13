# src/api/routes_auth.py

from __future__ import annotations

import secrets
from typing import Dict

from fastapi import APIRouter, HTTPException
from src.models.artifacts import AuthenticationRequest

router = APIRouter(tags=["auth"])

# token -> user info
TOKENS: Dict[str, dict] = {}

def _mint_token() -> str:
    return secrets.token_urlsafe(24)

@router.put("/authenticate", response_model=str)
def create_auth_token(req: AuthenticationRequest):
    if req is None or req.user is None or req.secret is None:
        raise HTTPException(status_code=400, detail="Malformed authentication request")

    password = (req.secret.password or "").strip()
    if password == "":
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = _mint_token()
    TOKENS[token] = {"name": req.user.name, "is_admin": bool(req.user.is_admin)}
    return token

def clear_tokens() -> None:
    TOKENS.clear()

#----------------OLD CODE BELOW-------------------

# from fastapi import APIRouter, HTTPException
# from src.models.artifacts import AuthenticationRequest

# router = APIRouter(tags=["auth"])


# @router.put("/authenticate")
# def create_auth_token(_req: AuthenticationRequest):
#     """
#     We are NOT implementing access-control track.
#     Per spec: return 501 and ignore X-Authorization on other endpoints.
#     """
#     raise HTTPException(status_code=501, detail="Authentication not implemented")
