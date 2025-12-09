"""
In-memory artifact registry backing the autograder-facing API.

This module is intentionally self-contained and does NOT depend on S3,
databases, or any external services. It is designed to:

- Store all artifacts created via POST /artifact/{artifact_type}
- Provide lookups for GET/PUT/DELETE /artifact/{artifact_type}/{id}
- Support POST /artifacts enumeration with offset-based pagination
- Support GET /artifact/byName/{name}
- Support POST /artifact/byRegEx
- Support DELETE /reset (via reset_store)

You can later add persistence (e.g., S3 or Postgres) behind these functions
without changing the API surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import uuid
import re
from datetime import datetime

from src.models.artifacts import (
    Artifact,
    ArtifactMetadata,
    ArtifactData,
    ArtifactQuery,
    ArtifactRegEx,
    ArtifactType,
)


# ---------------------------------------------------------------------------
# Internal model
# ---------------------------------------------------------------------------

@dataclass
class _ArtifactRecord:
    """Internal representation of an artifact entry in the registry."""
    artifact: Artifact
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


# Global in-memory store: artifact_id -> record
_ARTIFACTS: Dict[str, _ArtifactRecord] = {}


# ---------------------------------------------------------------------------
# ID generation & helpers
# ---------------------------------------------------------------------------

def generate_artifact_id() -> str:
    """
    Generate a new ArtifactID.

    The OpenAPI pattern is ^[a-zA-Z0-9\\-]+$, so we can safely use a
    truncated uuid4 hex string. Examples in the spec are numeric, but
    this is not required.
    """
    # 12 hex chars = 48 bits of entropy, plenty for collision resistance here.
    return uuid.uuid4().hex[:12]


def _infer_name_from_url(url: str) -> str:
    """
    Infer an artifact name from the source URL.

    Example: https://huggingface.co/openai/whisper -> "whisper"
    """
    if not url:
        return "artifact"
    # strip trailing slash and split by '/'
    parts = url.rstrip("/").split("/")
    # pick last non-empty segment
    for segment in reversed(parts):
        if segment:
            return segment
    return "artifact"


def _sorted_records() -> List[_ArtifactRecord]:
    """
    Return artifact records in a stable, deterministic order.

    We sort by (name, id) to make pagination consistent across calls.
    """
    return sorted(
        _ARTIFACTS.values(),
        key=lambda rec: (rec.artifact.metadata.name, rec.artifact.metadata.id),
    )


# ---------------------------------------------------------------------------
# CRUD API
# ---------------------------------------------------------------------------

def find_existing_artifact(
    artifact_type: ArtifactType,
    url: str,
) -> Optional[Artifact]:
    """
    Check if an artifact of the given type and source URL already exists.

    Used to implement HTTP 409 Conflict in POST /artifact/{artifact_type}.
    """
    for rec in _ARTIFACTS.values():
        art = rec.artifact
        if art.metadata.type == artifact_type and str(art.data.url) == url:
            return art
    return None


def create_artifact(artifact_type: ArtifactType, data: ArtifactData) -> Artifact:
    """
    Create a new artifact.

    - Infers name from data.url if the caller did not provide metadata.
    - Always creates a new ID (no implicit "update").
    - Does NOT check for duplicates; call find_existing_artifact first if you
      want to enforce uniqueness.
    """
    name = _infer_name_from_url(str(data.url))
    artifact_id = generate_artifact_id()

    metadata = ArtifactMetadata(
        name=name,
        id=artifact_id,
        type=artifact_type,
    )
    artifact = Artifact(metadata=metadata, data=data)

    rec = _ArtifactRecord(artifact=artifact)
    _ARTIFACTS[artifact_id] = rec
    return artifact


def get_artifact(artifact_type: ArtifactType, artifact_id: str) -> Optional[Artifact]:
    """
    Retrieve an artifact by type and id.

    Returns None if the artifact does not exist or the type does not match.
    """
    rec = _ARTIFACTS.get(artifact_id)
    if not rec:
        return None
    if rec.artifact.metadata.type != artifact_type:
        return None
    return rec.artifact


def update_artifact(
    artifact_type: ArtifactType,
    artifact_id: str,
    new_artifact: Artifact,
) -> Optional[Artifact]:
    """
    Update an existing artifact.

    Requirements (matching spec for PUT /artifact/{artifact_type}/{id}):

    - The artifact MUST already exist.
    - new_artifact.metadata.id MUST equal artifact_id
    - new_artifact.metadata.type MUST equal artifact_type
    - Name MAY be changed (spec allows replacing the source).

    Returns the updated artifact, or None if the artifact does not exist
    or metadata is inconsistent.
    """
    rec = _ARTIFACTS.get(artifact_id)
    if not rec:
        return None

    if new_artifact.metadata.id != artifact_id:
        # id mismatch -> invalid request
        return None
    if new_artifact.metadata.type != artifact_type:
        # type mismatch -> invalid request
        return None

    rec.artifact = new_artifact
    rec.updated_at = datetime.utcnow()
    _ARTIFACTS[artifact_id] = rec
    return new_artifact


def delete_artifact(artifact_type: ArtifactType, artifact_id: str) -> bool:
    """
    Delete an artifact if it exists and type matches.

    Returns True if deleted, False if not found / type mismatch.
    """
    rec = _ARTIFACTS.get(artifact_id)
    if not rec:
        return False
    if rec.artifact.metadata.type != artifact_type:
        return False
    del _ARTIFACTS[artifact_id]
    return True


# ---------------------------------------------------------------------------
# Enumeration & search
# ---------------------------------------------------------------------------

def list_artifacts(
    queries: List[ArtifactQuery],
    offset: Optional[str],
    page_size: int = 50,
) -> Tuple[List[ArtifactMetadata], str]:
    """
    Implement POST /artifacts:

    - `queries` is a non-empty list of ArtifactQuery.
    - If a query's name == "*", it matches all names.
    - If query.types is provided, we filter by those types.
    - Multiple queries are OR'ed: an artifact is included if it matches ANY.

    Pagination:

    - `offset` is a string representing an integer index into the full
      filtered result set (0-based).
    - We return at most `page_size` metadata entries.
    - We return the next_offset as a string, or "" if there are no more results.
      This goes into the `offset` response header per the spec.
    """
    # Flatten filters: we OR across queries.
    if not queries:
        return [], ""

    # Full list in deterministic order
    all_recs = _sorted_records()

    def matches(art: Artifact) -> bool:
        for q in queries:
            # Name check
            if q.name != "*" and art.metadata.name != q.name:
                continue
            # Type filtering
            if q.types is not None and art.metadata.type not in q.types:
                continue
            return True
        return False

    filtered: List[ArtifactMetadata] = []
    for rec in all_recs:
        if matches(rec.artifact):
            filtered.append(rec.artifact.metadata)

    # Pagination
    try:
        start = int(offset) if offset is not None and offset != "" else 0
    except ValueError:
        start = 0

    if start < 0:
        start = 0

    end = start + page_size
    page = filtered[start:end]

    if end < len(filtered):
        next_offset = str(end)
    else:
        next_offset = ""

    return page, next_offset


def list_by_name(name: str) -> List[ArtifactMetadata]:
    """
    Implement GET /artifact/byName/{name}.

    Returns metadata for all artifacts with this exact name.
    """
    results: List[ArtifactMetadata] = []
    for rec in _ARTIFACTS.values():
        art = rec.artifact
        if art.metadata.name == name:
            results.append(art.metadata)
    return sorted(results, key=lambda m: (m.name, m.id))


def search_by_regex(regex: ArtifactRegEx) -> List[ArtifactMetadata]:
    """
    Implement POST /artifact/byRegEx.

    The spec says search "over artifact names and READMEs".
    This implementation covers names only; you can extend it later to
    include README text once you map artifacts to S3 model cards.

    - regex.regex is interpreted as a Python regular expression.
    """
    pattern = re.compile(regex.regex)
    results: List[ArtifactMetadata] = []

    for rec in _ARTIFACTS.values():
        art = rec.artifact
        if pattern.search(art.metadata.name):
            results.append(art.metadata)
            continue

        # TODO: extend to README / card text if available:
        # card_text = get_model_card_text(...)
        # if pattern.search(card_text): ...

    return sorted(results, key=lambda m: (m.name, m.id))


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

def reset_store() -> None:
    """
    Clear all artifacts from the registry.

    Used by DELETE /reset.
    """
    _ARTIFACTS.clear()
