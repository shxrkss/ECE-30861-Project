# src/services/artifact_store.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import uuid
import re

from src.models.artifacts import (
    Artifact,
    ArtifactMetadata,
    ArtifactData,
    ArtifactQuery,
    ArtifactRegEx,
    ArtifactType,
)


@dataclass
class _ArtifactRecord:
    artifact: Artifact
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


# Global in-memory store: id -> record
_ARTIFACTS: Dict[str, _ArtifactRecord] = {}


def _new_id() -> str:
    """Generate an ArtifactID compatible with the regex ^[a-zA-Z0-9\\-]+$."""
    return uuid.uuid4().hex[:12]


def _infer_name_from_url(url: str) -> str:
    """Use last non-empty path segment as name."""
    if not url:
        return "artifact"
    parts = url.rstrip("/").split("/")
    for seg in reversed(parts):
        if seg:
            return seg
    return "artifact"


def _sorted_records() -> List[_ArtifactRecord]:
    """Deterministic ordering for pagination."""
    return sorted(
        _ARTIFACTS.values(),
        key=lambda r: (r.artifact.metadata.name, r.artifact.metadata.id),
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def find_existing_artifact(artifact_type: ArtifactType, url: str) -> Optional[Artifact]:
    """Return an existing artifact with same type+url if any, else None."""
    for rec in _ARTIFACTS.values():
        art = rec.artifact
        if art.metadata.type == artifact_type and str(art.data.url) == url:
            return art
    return None


def create_artifact(artifact_type: ArtifactType, data: ArtifactData) -> Artifact:
    """Create and store a new artifact."""
    name = _infer_name_from_url(str(data.url))
    art_id = _new_id()
    metadata = ArtifactMetadata(name=name, id=art_id, type=artifact_type)
    artifact = Artifact(metadata=metadata, data=data)
    _ARTIFACTS[art_id] = _ArtifactRecord(artifact=artifact)
    return artifact


def get_artifact(artifact_type: ArtifactType, art_id: str) -> Optional[Artifact]:
    rec = _ARTIFACTS.get(art_id)
    if not rec:
        return None
    if rec.artifact.metadata.type != artifact_type:
        return None
    return rec.artifact


def update_artifact(
    artifact_type: ArtifactType,
    art_id: str,
    new_artifact: Artifact,
) -> Optional[Artifact]:
    rec = _ARTIFACTS.get(art_id)
    if not rec:
        return None
    if new_artifact.metadata.id != art_id:
        return None
    if new_artifact.metadata.type != artifact_type:
        return None
    rec.artifact = new_artifact
    rec.updated_at = datetime.utcnow()
    _ARTIFACTS[art_id] = rec
    return new_artifact


def delete_artifact(artifact_type: ArtifactType, art_id: str) -> bool:
    rec = _ARTIFACTS.get(art_id)
    if not rec:
        return False
    if rec.artifact.metadata.type != artifact_type:
        return False
    del _ARTIFACTS[art_id]
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
    Implement POST /artifacts with offset pagination.
    Offset is a string index into the filtered list.
    """
    if not queries:
        return [], ""

    def matches(art: Artifact) -> bool:
        for q in queries:
            if q.name != "*" and art.metadata.name != q.name:
                continue
            if q.types is not None and art.metadata.type not in q.types:
                continue
            return True
        return False

    all_recs = _sorted_records()
    filtered: List[ArtifactMetadata] = [
        rec.artifact.metadata for rec in all_recs if matches(rec.artifact)
    ]

    try:
        start = int(offset) if offset not in (None, "") else 0
    except ValueError:
        start = 0
    if start < 0:
        start = 0

    end = start + page_size
    page = filtered[start:end]
    next_offset = str(end) if end < len(filtered) else ""

    return page, next_offset


def list_by_name(name: str) -> List[ArtifactMetadata]:
    results: List[ArtifactMetadata] = []
    for rec in _ARTIFACTS.values():
        if rec.artifact.metadata.name == name:
            results.append(rec.artifact.metadata)
    return sorted(results, key=lambda m: (m.name, m.id))


def search_by_regex(regex: ArtifactRegEx) -> List[ArtifactMetadata]:
    pattern = re.compile(regex.regex)
    results: List[ArtifactMetadata] = []
    for rec in _ARTIFACTS.values():
        art = rec.artifact
        if pattern.search(art.metadata.name):
            results.append(art.metadata)
    return sorted(results, key=lambda m: (m.name, m.id))


def reset_store():
    global _ARTIFACTS
    _ARTIFACTS = {
        "model": {},
        "dataset": {},
        "code": {}
    }