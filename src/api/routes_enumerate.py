from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from src.services.s3_service import list_s3_models, search_models_by_card
import re
from src.models.model_metadata import ModelMetadata

router = APIRouter(prefix="/api", tags=["enumerate"])

@router.get("/enumerate", response_model=List[ModelMetadata])
def enumerate_models(
    name_regex: Optional[str] = Query(None, description="Regex to match model names"),
    card_regex: Optional[str] = Query(None, description="Regex to match model card text"),
    version: Optional[str] = Query(None, description="Exact version string"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100)
):
    """List models with optional regex filters for name and card content."""
    try:
        all_models = list_s3_models()
        filtered = all_models

        if name_regex:
            filtered = [m for m in filtered if re.search(name_regex, m['name'], re.IGNORECASE)]

        if card_regex:
            filtered = search_models_by_card(filtered, card_regex)

        # Pagination
        start, end = (page - 1) * limit, page * limit
        paginated = filtered[start:end]

        return [ModelMetadata(**m) for m in paginated]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enumeration failed: {e}")