from fastapi import FastAPI
from mangum import Mangum

from src.api import (
    routes_health,
    routes_artifacts,
    routes_model_extras,
    routes_reset,
    routes_auth,
    routes_tracks,
)

app = FastAPI(
    title="ECE 461 / Phase 2 Backend",
    version="1.0.0",
)

# Include routers
app.include_router(routes_health.router)
app.include_router(routes_artifacts.router)
app.include_router(routes_model_extras.router)
app.include_router(routes_reset.router)
app.include_router(routes_auth.router)
app.include_router(routes_tracks.router)
app.include_router(routes_model_extras.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "backend online"}

# Lambda entrypoint
handler = Mangum(app)
