# src/api/routes_health.py
from fastapi import APIRouter, Query
from datetime import datetime, timezone

router = APIRouter(tags=["health"])


@router.get("/health")
def registry_health_heartbeat():
    """
    Lightweight liveness probe.
    Spec only requires HTTP 200.
    """
    return {"status": "ok"}


@router.get("/health/components")
def registry_health_components(
    windowMinutes: int = Query(60, ge=5, le=1440),
    includeTimeline: bool = Query(False),
):
    """
    NON-BASELINE: health/component details.
    We return a minimal object consistent with HealthComponentCollection schema.
    """
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Minimal, spec-shaped HealthComponentCollection
    body = {
        "components": [
            {
                "id": "api-server",
                "display_name": "API Server",
                "status": "ok",
                "observed_at": now,
                "description": "FastAPI application",
                "metrics": {},
                "issues": [],
                "timeline": [] if includeTimeline else [],
                "logs": [],
            }
        ],
        "generated_at": now,
        "window_minutes": windowMinutes,
    }
    return body
