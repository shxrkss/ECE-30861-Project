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


# NOTE: No /api prefix — paths must match the autograder spec exactly.
app.include_router(routes_health.router)
app.include_router(routes_artifacts.router)
app.include_router(routes_model_extras.router)
app.include_router(routes_reset.router)
app.include_router(routes_auth.router)
app.include_router(routes_tracks.router)


# Optional root
@app.get("/")
def root():
    return {"message": "Artifact Registry running"}
