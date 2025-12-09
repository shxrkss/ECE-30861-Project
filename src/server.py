# src/server.py
import os
from fastapi import FastAPI, Depends
from src.log import setup_logging
from src.api import routes_models, routes_enumerate, routes_ingest, routes_license, routes_admin
from src.services.auth import verify_api_key
from src.services.health_events import summarize_recent
from src.services.s3_service import list_s3_models
from src.log import logger
import asyncio
from fastapi import Request


# Configure logging first
setup_logging()

# Protect docs in production by default. If ALLOW_OPEN_DOCS=1 then keep docs public (convenience)
ALLOW_OPEN_DOCS = os.getenv("ALLOW_OPEN_DOCS", "0") == "1"
docs_url = "/docs" if ALLOW_OPEN_DOCS else None
redoc_url = "/redoc" if ALLOW_OPEN_DOCS else None

app = FastAPI(title="Trustworthy Model Registry", docs_url=docs_url, redoc_url=redoc_url)

# Mount routers
app.include_router(routes_models.router, prefix="/api")
app.include_router(routes_enumerate.router, prefix="/api")
app.include_router(routes_ingest.router, prefix="/api")
app.include_router(routes_license.router, prefix="/api")
app.include_router(routes_admin.router, prefix="/api")

@app.get("/")
def root():
    return {"status": "running", "message": "Trustworthy Model Registry — API is running", "docs": "/docs" if ALLOW_OPEN_DOCS else "protected"}

# Example health endpoint remains open
@app.get("/health")
def health():
    return {"status": "OK"}

@app.get("/debug-log")
def debug_log():
    logger.info("debug-log endpoint hit")
    return {"ok": True}

REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15.0"))

@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    try:
        return await asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT)
    except asyncio.TimeoutError:
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "Request timed out"}, status_code=504)
    
@app.get("/health/metrics")
def health_metrics():
    """
    Health data feed for the dashboard:
    - recent event counts (last 60 minutes)
    - current number of models in registry
    """
    try:
        models = list_s3_models()
        model_count = len(models)
    except Exception:
        model_count = -1

    summary = summarize_recent(minutes=60)
    summary["model_count"] = model_count
    return summary
