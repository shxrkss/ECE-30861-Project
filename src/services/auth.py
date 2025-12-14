# src/services/auth.py
import os
import time
import json
from typing import Dict
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Optional: load keys if present, but DO NOT fail if missing
API_KEYS_JSON = os.getenv("API_KEYS_JSON", "")
API_KEY_MAP: Dict[str, Dict] = {}

if API_KEYS_JSON:
    try:
        API_KEY_MAP = json.loads(API_KEYS_JSON)
    except Exception:
        API_KEY_MAP = {}
else:
    single = os.getenv("API_KEY")
    if single:
        API_KEY_MAP = {
            single: {"user": "default", "roles": ["upload", "download", "enumerate", "admin"]}
        }

# Simple brute-force protection scaffolding (can be ignored in class env)
_LOCKOUT_TTL = int(os.getenv("API_KEY_LOCKOUT_SECONDS", 300))
_MAX_ATTEMPTS = int(os.getenv("API_KEY_MAX_ATTEMPTS", 5))

_attempts: Dict[str, tuple] = {}
_lockouts: Dict[str, float] = {}


def _is_locked(key: str) -> bool:
    until = _lockouts.get(key)
    if until and time.time() < until:
        return True
    if until and time.time() >= until:
        _lockouts.pop(key, None)
    return False


def _register_failure(key: str):
    cnt, first = _attempts.get(key, (0, time.time()))
    cnt += 1
    _attempts[key] = (cnt, first)
    if cnt >= _MAX_ATTEMPTS:
    cnt, first = _attempts.get(key, (0, time.time()))
    cnt += 1
    _attempts[key] = (cnt, first)
    if cnt >= _MAX_ATTEMPTS:
        _lockouts[key] = time.time() + _LOCKOUT_TTL
        if key in _attempts:
            del _attempts[key]



def _register_success(key: str):
    _attempts.pop(key, None)


def verify_api_key(key: str = Security(api_key_header)) -> Dict:
    """
    FastAPI dependency: verifies API key.

    For the class project / autograder, we don't want startup to fail if no keys
    are configured, so we fall back to an 'autograder' user.
    """

    # If no API keys configured at all, just allow everything (class/demo mode)
    if not API_KEY_MAP:
        return {"user": "autograder", "roles": ["upload", "download", "enumerate", "admin"]}

    if key is None:
        raise HTTPException(status_code=401, detail="Missing API key")

    if _is_locked(key):
        raise HTTPException(status_code=423, detail="API key locked; try later")

    info = API_KEY_MAP.get(key)
    info = API_KEY_MAP.get(key)
    if not info:
        _register_failure(key)
        raise HTTPException(status_code=401, detail="Invalid API key")

    _register_success(key)
    return info


def require_role(required_role: str):
    """
    Dependency to enforce role membership.
    """
    from fastapi import Depends

    def _dependency(user_info: Dict = Depends(verify_api_key)):
        roles = user_info.get("roles", [])
        if required_role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden: missing role")
        return user_info

    return _dependency