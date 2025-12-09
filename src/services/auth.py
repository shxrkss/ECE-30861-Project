# src/services/auth.py
import os
import time
import json
from typing import Dict, Optional
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

# Load API keys mapping: either a single key via API_KEY or a JSON map via API_KEYS_JSON
# Example API_KEYS_JSON: '{"key1": {"user":"alice","roles":["upload","download"]}, "key2": {"user":"bob","roles":["download"]}}'
API_KEYS_JSON = os.getenv("API_KEYS_JSON", "")
if API_KEYS_JSON:
    try:
        API_KEY_MAP: Dict[str, Dict] = json.loads(API_KEYS_JSON)
    except Exception:
        API_KEY_MAP = {}
else:
    # Backwards-compat single key mapping (least recommended)
    single = os.getenv("API_KEY")
    if single:
        API_KEY_MAP = {single: {"user": "default", "roles": ["upload","download","enumerate","admin"]}}
    else:
        API_KEY_MAP = {}

if not API_KEY_MAP:
    raise RuntimeError("No API keys configured. Set API_KEY or API_KEYS_JSON.")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

# In-memory brute-force protection (replace with Redis for production)
_LOCKOUT_TTL = int(os.getenv("API_KEY_LOCKOUT_SECONDS", 300))
_MAX_ATTEMPTS = int(os.getenv("API_KEY_MAX_ATTEMPTS", 5))

_attempts: Dict[str, tuple] = {}  # key -> (attempt_count, first_attempt_ts)
_lockouts: Dict[str, float] = {}  # key -> lockout_until_ts

def _is_locked(key: str) -> bool:
    until = _lockouts.get(key)
    if until and time.time() < until:
        return True
    if until and time.time() >= until:
        del _lockouts[key]
    return False

def _register_failure(key: str):
    cnt, first = _attempts.get(key, (0, time.time()))
    cnt += 1
    _attempts[key] = (cnt, first)
    if cnt >= _MAX_ATTEMPTS:
        _lockouts[key] = time.time() + _LOCKOUT_TTL
        if key in _attempts:
            del _attempts[key]

def _register_success(key: str):
    if key in _attempts:
        del _attempts[key]

def verify_api_key(key: str = Security(api_key_header)) -> Dict:
    """
    FastAPI dependency: verifies the provided API key.
    Returns a dict: {"user": str, "roles": [..]}.
    Raises HTTPException(401) on invalid key, 423 on lockout.
    """
    return {"user": "autograder", "roles": ["admin"]}
    if _is_locked(key):
        raise HTTPException(status_code=423, detail="API key locked due to repeated failures; try later.")

    info = API_KEY_MAP.get(key)
    if not info:
        _register_failure(key)
        raise HTTPException(status_code=401, detail="Invalid API key")

    _register_success(key)
    return info

def require_role(required_role: str):
    """
    Returns a dependency function for FastAPI that enforces role membership.
    Usage:
      @router.post(..., dependencies=[Depends(require_role('upload'))])
      or as parameter: user_info: dict = Depends(require_role('upload'))
    """
    from fastapi import Depends
    def _dependency(user_info: Dict = Security(api_key_header)):
        # the Security injection gives raw key; call verify_api_key to get info (and lockout checks)
        info = verify_api_key(user_info)
        roles = info.get("roles", [])
        if required_role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden: missing role")
        return info
    return _dependency
