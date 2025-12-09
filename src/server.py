# src/server.py
from fastapi import FastAPI

from src.api import (
    routes_health,
    routes_artifacts,
    routes_model_extras,
    routes_reset,
    routes_auth,
    routes_tracks,
)

app = FastAPI(
    title="ECE 461 / Fall 2025 / Phase 2 - Trustworthy Artifact Registry",
    version="1.0.0",
)

app.include_router(routes_health.router)
app.include_router(routes_artifacts.router)
app.include_router(routes_model_extras.router)
app.include_router(routes_reset.router)
app.include_router(routes_auth.router)
app.include_router(routes_tracks.router)
app.include_router(routes_model_extras.router, prefix="/api")


@app.get("/")
def root():
    # simple root for Lighthouse
    return {"message": "Artifact Registry running"}
