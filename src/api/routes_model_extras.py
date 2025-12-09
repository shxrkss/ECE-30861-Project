# src/api/routes_model_extras.py
from src.services.auth import require_role
from fastapi import APIRouter, HTTPException, Path, Query, Header, Depends

from src.models.artifacts import (
    ModelRating,
    ArtifactLineageGraph,
    SimpleLicenseCheckRequest,
    ArtifactCost,
    ArtifactType,
)
from src.services.artifact_store import get_artifact
from src.services.rating_engine import compute_model_rating
from src.services.lineage_engine import compute_lineage_graph
from src.services.cost_engine import compute_artifact_cost

router = APIRouter(tags=["model-extras"])

@router.get("/enumerate", dependencies=[Depends(require_role("enumerate"))])
def enumerate_route():
    return enumerate_models()


def require_auth(x_authorization: str = Header(..., alias="X-Authorization")):
    return x_authorization


@router.get("/artifact/model/{id}/rate", response_model=ModelRating)
def model_artifact_rate(
    id: str = Path(...),
    _token: str = Depends(require_auth),
):
    art = get_artifact(ArtifactType.model, id)
    if not art:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    try:
        rating = compute_model_rating(art)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="The artifact rating system encountered an error.",
        )
    return rating


@router.get("/artifact/model/{id}/lineage", response_model=ArtifactLineageGraph)
def model_artifact_lineage(
    id: str = Path(...),
    _token: str = Depends(require_auth),
):
    art = get_artifact(ArtifactType.model, id)
    if not art:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    graph = compute_lineage_graph(art)
    if not graph:
        raise HTTPException(
            status_code=400,
            detail="The lineage graph cannot be computed because the artifact metadata is missing or malformed.",
        )
    return graph


@router.post("/artifact/model/{id}/license-check", response_model=bool)
def artifact_license_check(
    id: str = Path(...),
    req: SimpleLicenseCheckRequest = ...,
    _token: str = Depends(require_auth),
):
    art = get_artifact(ArtifactType.model, id)
    if not art:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    if not req.github_url:
        raise HTTPException(
            status_code=400,
            detail="The license check request is malformed or references an unsupported usage context.",
        )

    # We don't implement real license logic for baseline – always return True.
    return True


@router.get("/artifact/{artifact_type}/{id}/cost", response_model=ArtifactCost)
def artifact_cost(
    artifact_type: ArtifactType = Path(...),
    id: str = Path(...),
    dependency: bool = Query(False),
    _token: str = Depends(require_auth),
):
    art = get_artifact(artifact_type, id)
    if not art:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    try:
        cost = compute_artifact_cost(art, include_dependencies=dependency)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="The artifact cost calculator encountered an error.",
        )
    return cost
