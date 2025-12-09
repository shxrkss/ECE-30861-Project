from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional
from src.services.s3_service import list_s3_models, search_models_by_card, get_model_card_text
from src.models.model_metadata import ModelMetadata
from src.services.auth import verify_api_key
from src.services.sanitize import redact_urls
from src.services.rate_limit import rate_limiter, enforce_rate_limit
import re


router = APIRouter(
    tags=["enumerate"],
    dependencies=[Depends(enforce_rate_limit)]
)

@router.get("/enumerate", response_model=List[ModelMetadata])
async def enumerate_models(
    authorized: bool = Depends(verify_api_key),
    name_regex: Optional[str] = Query(None),
    card_regex: Optional[str] = Query(None),
    version: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    user_info: dict = Depends(verify_api_key)
):
    """
    List models with optional regex filters for name and card content.
    Now also attaches a URL-redacted snippet of the model card.
    """
    try:
        all_models = list_s3_models()
        filtered = all_models

        if name_regex:
            filtered = [
                m for m in filtered
                if re.search(name_regex, m["name"], re.IGNORECASE)
            ]

        if card_regex:
            # this already uses get_model_card_text internally to filter by regex
            filtered = search_models_by_card(filtered, card_regex)

        # Pagination
        start, end = (page - 1) * limit, page * limit
        paginated = filtered[start:end]

        enriched = []
        for m in paginated:
            # Fetch full card text (README or metadata.json) — may be empty
            card_text = get_model_card_text(m["key"])
            # Make a short, redacted snippet for display
            snippet_raw = card_text[:1000] if card_text else ""
            snippet_safe = redact_urls(snippet_raw)

            data = dict(m)  # copy the S3 metadata dict
            # Assumes ModelMetadata has an optional `card_snippet: Optional[str]` field
            data["card_snippet"] = snippet_safe

            enriched.append(ModelMetadata(**data))

        return enriched

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enumeration failed: {e}")
