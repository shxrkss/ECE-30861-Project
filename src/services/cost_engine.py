# src/services/cost_engine.py
from typing import Dict, Any
from src.models.artifacts import ArtifactCost


def compute_artifact_cost(artifact, include_dependencies: bool) -> ArtifactCost:
    """
    Compute a fake but deterministic "size cost" based on URL length.
    No external services or S3 required.
    """
    url_str = str(artifact.data.url) if artifact.data and artifact.data.url else ""
    base_cost = round(10.0 + (len(url_str) % 50), 1)  # between 10.0 and 59.9

    entry: Dict[str, Any] = {"total_cost": base_cost}
    if include_dependencies:
        entry["standalone_cost"] = base_cost

    return {artifact.metadata.id: entry}
