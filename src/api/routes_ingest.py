# src/api/routes_ingest.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
import tempfile
import hashlib
import logging
import requests
from huggingface_hub import hf_hub_download


from src.services.auth import verify_api_key
from src.services.rate_limit import enforce_rate_limit
from src.services.s3_service import upload_file_to_s3, write_manifest
from orchestrator import run_all_metrics  # metrics assumed implemented

logger = logging.getLogger("trustworthy-registry")

router = APIRouter(
    tags=["ingest"],
    dependencies=[Depends(enforce_rate_limit)],
)

class IngestRequest(BaseModel):
    model_id: str         # e.g. "owner/name" on HuggingFace
    code_url: str | None = None
    dataset_url: str | None = None


@router.post("/ingest")
def ingest_model(
    req: IngestRequest,
    user_info: dict = Depends(verify_api_key),
):
    """
    Ingest a public HuggingFace model into the registry.
    1. Run all metrics.
    2. If all non-latency metrics >= 0.5, download model artifact.
    3. Upload to S3 and write manifest.
    """

    # Build model URL for metrics (your metric code already knows how to handle HF URLs)
    model_url = f"https://huggingface.co/{req.model_id}".rstrip("/")
    repo_info = (req.code_url, req.dataset_url, model_url)

    metrics = run_all_metrics(repo_info)

    # Enforce ingestability: all non-latency metrics >= 0.5
    # Adjust this list to align with your metric keys (reproducibility, reviewedness, etc.)
    metric_keys = [
        "ramp_up_time",
        "bus_factor",
        "performance_claims",
        "license",
        "dataset_quality",
        "code_quality",
        "reproducibility",
        "reviewedness",
        "treescore",
    ]

    failing = {
        k: metrics.get(k)
        for k in metric_keys
        if metrics.get(k) is not None and metrics.get(k) < 0.5
    }

    if failing:
        raise HTTPException(
            status_code=400,
            detail={
                "reason": "Model did not meet ingest thresholds",
                "failing_metrics": failing,
            },
        )

    # TODO: replace this naive HTTP download with huggingface_hub.hf_hub_download
    # For now, assume an externally prepared ZIP URL is provided via dataset_url or code_url if needed.
    path = hf_hub_download(repo_id=req.model_id, filename="model.safetensors")

    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            resp = requests.get(path, stream=True, timeout=60)
            resp.raise_for_status()
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                if chunk:
                    tmp.write(chunk)
            tmp.flush()
            tmp_path = tmp.name
    except Exception as e:
        logger.exception("Failed to download model during ingest")
        raise HTTPException(status_code=502, detail=f"Failed to download model artifact: {e}")

    # Compute checksum
    h = hashlib.sha256()
    with open(tmp_path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    checksum = h.hexdigest()

    # Canonical filename based on model_id
    filename = f"{req.model_id.replace('/', '__')}.zip"
    s3_key = f"models/{filename}"

    upload_file_to_s3(tmp_path, s3_key, checksum=checksum)

    manifest = {
        "uploader": user_info.get("user", "unknown"),
        "checksum": checksum,
        "filename": filename,
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
        "notes": "manifest auto-generated from HuggingFace ingest",
        "source": {
            "type": "huggingface",
            "model_id": req.model_id,
            "code_url": req.code_url,
            "dataset_url": req.dataset_url,
        },
        "full_s3_key": s3_key,
        "weights_s3_key": None,
        "dataset_s3_key": None,
        "metrics": metrics,
    }
    write_manifest(s3_key, manifest)

    return {
        "success": True,
        "filename": filename,
        "metrics": metrics,
    }
