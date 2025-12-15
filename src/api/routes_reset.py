# src/api/routes_reset.py
# from fastapi import APIRouter, Header, Depends

# from src.services.artifact_store import reset_store
# from src.api.routes_health import REQUESTS, ERRORS, DOWNLOADS, LATENCIES
# from src.api.routes_auth import clear_tokens

# router = APIRouter(tags=["admin"])

# def require_auth(x_authorization: str | None = Header(None, alias="X-Authorization")):
#     return x_authorization or ""

# @router.delete("/reset")
# def registry_reset(_token: str = Depends(require_auth)):
#     reset_store()
#     clear_tokens()
#     REQUESTS.clear()
#     ERRORS.clear()
#     DOWNLOADS.clear()
#     LATENCIES.clear()
#     return {"status": "Registry is reset."}

# @router.put("/reset")
# def registry_reset_put(_token: str = Depends(require_auth)):
#     return registry_reset(_token)

# @router.post("/reset")
# def registry_reset_post(_token: str = Depends(require_auth)):
#     return registry_reset(_token)

#-----------------OLD CODE BELOW---------------------------

# from fastapi import APIRouter
# from src.services.artifact_store import reset_store
# from src.services.rate_limit import reset_rate_limit_state

# router = APIRouter(tags=["reset"])

# @router.post("/reset")
# def reset_system():
#     reset_store()
#     reset_rate_limit_state()
#     return {"status": "ok"}
#---------------------------Ore's Code Below-----------------------------------------------------

from fastapi import APIRouter #, Header, Depends, HTTPException
from src.services.artifact_store import reset_store
#from src.services.rate_limit import reset_rate_limit_state
from src.api.routes_health import REQUESTS, ERRORS, DOWNLOADS, LATENCIES
router = APIRouter(tags=["admin"])

@router.post("/reset")
@router.put("/reset")
@router.delete("/reset")
def reset():
    reset_store()
    REQUESTS.clear()
    ERRORS.clear()
    DOWNLOADS.clear()
    LATENCIES.clear()
    return {"status": "ok"}
