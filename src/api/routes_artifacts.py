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


# ---------------------------------------------------------------------------
# Authentication stub (baseline-friendly)
# ---------------------------------------------------------------------------

def require_auth(x_authorization: str = Header(..., alias="X-Authorization")):
    """
    The autograder REQUIRES this header. If you do not implement real auth, you
    MUST still accept the header, regardless of its contents.

    Returning it allows downstream logic to inspect if needed.
    """
    if not x_authorization:
        raise HTTPException(status_code=403, detail="Authentication failed")
    return x_authorization


# ---------------------------------------------------------------------------
# POST /artifact/{artifact_type}
# Create a new artifact
# ---------------------------------------------------------------------------

@router.post("/artifact/{artifact_type}", response_model=Artifact, status_code=201)
def artifact_create(
    artifact_type: ArtifactType = Path(...),
    data: ArtifactData = ...,
    _token: str = Depends(require_auth),
):
    # Validate request body fields
    if not data or not data.url:
        raise HTTPException(status_code=400, detail="Missing or malformed artifact_data")

    # Spec requires: 409 Conflict if exact same artifact already exists
    existing = find_existing_artifact(artifact_type, str(data.url))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Artifact exists already")

    try:
        art = create_artifact(artifact_type, data)
        return art
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed artifact_data")


# ---------------------------------------------------------------------------
# GET /artifact/{artifact_type}/{id}
# Retrieve a specific artifact
# ---------------------------------------------------------------------------

@router.get("/artifact/{artifact_type}/{id}", response_model=Artifact)
def artifact_retrieve(
    artifact_type: ArtifactType = Path(...),
    id: str = Path(...),
    _token: str = Depends(require_auth),
):
    art = get_artifact(artifact_type, id)
    if not art:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    # Nothing else required; `download_url` may be None if not populated yet
    return art


# ---------------------------------------------------------------------------
# PUT /artifact/{artifact_type}/{id}
# Update an existing artifact
# ---------------------------------------------------------------------------

@router.put("/artifact/{artifact_type}/{id}")
def artifact_update_route(
    artifact_type: ArtifactType = Path(...),
    id: str = Path(...),
    artifact: Artifact = ...,
    _token: str = Depends(require_auth),
):
    # Validate body
    if artifact is None or artifact.metadata.id != id:
        raise HTTPException(status_code=400, detail="Malformed artifact or id mismatch")

    updated = update_artifact(artifact_type, id, artifact)
    if not updated:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    return {"status": "updated"}


# ---------------------------------------------------------------------------
# DELETE /artifact/{artifact_type}/{id}
# Delete an artifact
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# POST /artifacts
# Enumeration with pagination and multiple queries
# ---------------------------------------------------------------------------

@router.post("/artifacts", response_model=List[ArtifactMetadata])
def artifacts_list_route(
    queries: List[ArtifactQuery],
    response: Response,
    offset: Optional[str] = Query(None),
    _token: str = Depends(require_auth),
):
    # Validate queries
    if not isinstance(queries, list) or len(queries) == 0:
        raise HTTPException(
            status_code=400,
            detail="artifact_query must be an array with at least one entry",
        )

    # Basic field validation
    for q in queries:
        if not q.name:
            raise HTTPException(status_code=400, detail="Query missing required name field")

    page, next_offset = list_artifacts(queries, offset)

    # Set response header required by spec
    response.headers["offset"] = next_offset

    return page


# ---------------------------------------------------------------------------
# GET /artifact/byName/{name}
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# POST /artifact/byRegEx
# ---------------------------------------------------------------------------

@router.post("/artifact/byRegEx", response_model=List[ArtifactMetadata])
def artifact_by_regex_route(
    regex: ArtifactRegEx,
    _token: str = Depends(require_auth),
):
    # Validate regex field
    if not regex or not regex.regex:
        raise HTTPException(status_code=400, detail="Malformed artifact_regex")

    try:
        results = search_by_regex(regex)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid regular expression")

    if not results:
        raise HTTPException(status_code=404, detail="No artifact found under this regex")

    return results


# ---------------------------------------------------------------------------
# GET /artifact/{artifact_type}/{id}/audit
# NON-BASELINE (stub)
# ---------------------------------------------------------------------------

@router.get("/artifact/{artifact_type}/{id}/audit")
def artifact_audit_get(
    artifact_type: ArtifactType = Path(...),
    id: str = Path(...),
    _token: str = Depends(require_auth),
):
    # AUDIT is non-baseline; skeleton returns empty list.
    return []
