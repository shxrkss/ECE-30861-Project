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

@app.get("/api/s3-test")
def s3_test():
    import boto3, os
    bucket = os.getenv("AWS_BUCKET_NAME")
    s3 = boto3.client("s3")

    # Try listing contents
    try:
        response = s3.list_objects_v2(Bucket=bucket)
        return {
            "status": "ok",
            "bucket": bucket,
            "contents": response.get("Contents", []),
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "bucket": bucket}
    
print("DEPLOY TEST")
