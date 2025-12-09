# src/api/routes_admin.py
from fastapi import APIRouter, HTTPException, Depends
from src.services.auth import verify_api_key
from src.services.rate_limit import enforce_rate_limit, reset_rate_limit_state
from src.services.s3_service import delete_prefix
from src.services.health_events import record_event

router = APIRouter(
    tags=["admin"],
    dependencies=[Depends(enforce_rate_limit)],
)


@router.post("/reset")
def reset_registry(user_info: dict = Depends(verify_api_key)):
    """
    Reset registry to default state:
    - Delete all models under 'models/' in S3.
    - Clear in-memory rate limiter state.
    Requires an 'admin' role on the user.
    """
    roles = user_info.get("roles", [])
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="Admin role required for reset")

    deleted = delete_prefix("models/")
    reset_rate_limit_state()
    record_event("reset", user_info.get("user"))
    return {
        "success": True,
        "deleted_objects": deleted,
        "message": "Registry reset to empty models and cleared in-memory rate limits",
    }
