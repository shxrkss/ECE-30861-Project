# src/api/routes_artifacts.py
from fastapi import (
    APIRouter,
    HTTPException,
    Path,
    Query,
    Header,
    Depends,
    Response,
)
from typing import List, Optional

from src.models.artifacts import (
    Artifact,
    ArtifactData,
    ArtifactMetadata,
    ArtifactQuery,
    ArtifactRegEx,
    ArtifactType,
)
from src.services.artifact_store import (
    create_artifact,
    get_artifact,
    update_artifact,
    delete_artifact,
    list_artifacts,
    list_by_name,
    search_by_regex,
    find_existing_artifact,
)

router = APIRouter(tags=["artifacts"])


def require_auth(x_authorization: str = Header(..., alias="X-Authorization")):
    """
    In 'no auth' mode we just require the header to exist and ignore it.
    """
    return x_authorization


@router.post("/artifact/{artifact_type}", response_model=Artifact, status_code=201)
def artifact_create(
    artifact_type: ArtifactType = Path(...),
    data: ArtifactData = ...,
    _token: str = Depends(require_auth),
):
    if not data or not data.url:
        raise HTTPException(status_code=400, detail="Missing or malformed artifact_data")

    existing = find_existing_artifact(artifact_type, str(data.url))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Artifact exists already")

    art = create_artifact(artifact_type, data)
    return art


@router.get("/artifact/{artifact_type}/{id}", response_model=Artifact)
def artifact_retrieve(
    artifact_type: ArtifactType = Path(...),
    id: str = Path(...),
    _token: str = Depends(require_auth),
):
    art = get_artifact(artifact_type, id)
    if not art:
        raise HTTPException(status_code=404, detail="Artifact does not exist")
    return art


@router.put("/artifact/{artifact_type}/{id}")
def artifact_update_route(
    artifact_type: ArtifactType = Path(...),
    id: str = Path(...),
    artifact: Artifact = ...,
    _token: str = Depends(require_auth),
):
    if artifact is None or artifact.metadata.id != id:
        raise HTTPException(status_code=400, detail="Malformed artifact or id mismatch")

    updated = update_artifact(artifact_type, id, artifact)
    if not updated:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    return {"status": "updated"}


@router.delete("/artifact/{artifact_type}/{id}")
def artifact_delete_route(
    artifact_type: ArtifactType = Path(...),
    id: str = Path(...),
    _token: str = Depends(require_auth),
):
    ok = delete_artifact(artifact_type, id)
    if not ok:
        raise HTTPException(status_code=404, detail="Artifact does not exist")
    return {"status": "deleted"}


@router.post("/artifacts", response_model=List[ArtifactMetadata])
def artifacts_list_route(
    queries: List[ArtifactQuery],
    response: Response,
    offset: Optional[str] = Query(None),
    _token: str = Depends(require_auth),
):
    if not isinstance(queries, list) or len(queries) == 0:
        raise HTTPException(
            status_code=400,
            detail="artifact_query must be an array with at least one entry",
        )
    for q in queries:
        if not q.name:
            raise HTTPException(status_code=400, detail="Query missing required name field")

    page, next_offset = list_artifacts(queries, offset)
    response.headers["offset"] = next_offset
    return page


@router.get("/artifact/byName/{name}", response_model=List[ArtifactMetadata])
def artifact_by_name_route(
    name: str = Path(...),
    _token: str = Depends(require_auth),
):
    if not name:
        raise HTTPException(status_code=400, detail="Missing artifact name")

    results = list_by_name(name)
    if not results:
        raise HTTPException(status_code=404, detail="No such artifact")
    return results


@router.post("/artifact/byRegEx", response_model=List[ArtifactMetadata])
def artifact_by_regex_route(
    regex: ArtifactRegEx,
    _token: str = Depends(require_auth),
):
    if not regex or not regex.regex:
        raise HTTPException(status_code=400, detail="Malformed artifact_regex")

    try:
        results = search_by_regex(regex)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid regular expression")

    if not results:
        raise HTTPException(status_code=404, detail="No artifact found under this regex")
    return results


@router.get("/artifact/{artifact_type}/{id}/audit")
def artifact_audit_get(
    artifact_type: ArtifactType = Path(...),
    id: str = Path(...),
    _token: str = Depends(require_auth),
):
    # NON-BASELINE stub – empty audit trail
    return []
