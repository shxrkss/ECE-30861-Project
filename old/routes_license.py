# src/api/routes_license.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os

from src.services.auth import verify_api_key
from src.services.rate_limit import enforce_rate_limit
from src.services.license_compat import (
    get_github_license_spdx,
    get_hf_model_license,
    assess_compatibility,
)

router = APIRouter(
    tags=["license"],
    dependencies=[Depends(enforce_rate_limit)],
)

class LicenseCheckRequest(BaseModel):
    github_url: str
    model_id: str  # huggingface model id, e.g. "owner/name"


@router.post("/license-compatibility")
def license_compatibility(
    req: LicenseCheckRequest,
    user_info: dict = Depends(verify_api_key),
):
    """
    Check if a GitHub repo's license is compatible with a model's license
    for fine-tune + inference/generation.
    """
    gh_token = os.getenv("GITHUB_TOKEN")  # optional, for higher rate limits

    try:
        gh_license = get_github_license_spdx(req.github_url, token=gh_token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to determine GitHub license: {e}")

    try:
        model_license = get_hf_model_license(req.model_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to determine model license: {e}")

    compatible, reason = assess_compatibility(model_license, gh_license)

    return {
        "github_license": gh_license,
        "model_license": model_license,
        "compatible": compatible,
        "reason": reason,
    }
