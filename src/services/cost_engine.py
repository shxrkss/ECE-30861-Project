# src/services/cost_engine.py
from typing import Dict, Any
from src.models.artifacts import ArtifactCost
from src.services.s3_service import get_s3_client, get_bucket_name


def compute_artifact_cost(artifact, include_dependencies: bool) -> ArtifactCost:
    """
    Compute a fake but deterministic "size cost" based on URL length.
    No external services or S3 required.
    """
    s3 = get_s3_client()
    bucket = get_bucket_name()
    url_str = str(artifact.data.url) if artifact.data and artifact.data.url else ""
    base_cost = round(10.0 + (len(url_str) % 50), 1)  # between 10.0 and 59.9

    key = artifact.data.download_url or artifact.data.url
    if not key:
        raise RuntimeError("Artifact missing blob reference")

    # Extract S3 key from a full URL if necessary
    if "amazonaws.com" in key:
        s3_key = key.split("/")[-1]
    else:
        s3_key = key

    # HEAD request to get object size
    head = s3.head_object(Bucket=bucket, Key=s3_key)
    size_bytes = head["ContentLength"]
    mb = round(size_bytes / (1024 * 1024), 1)

    result: Dict[str, Dict[str, float]] = {
        artifact.metadata.id: {
            "total_cost": mb
        }
    }

    entry: Dict[str, Any] = {"total_cost": base_cost}
    if include_dependencies:
        entry["standalone_cost"] = base_cost

    return {artifact.metadata.id: entry}