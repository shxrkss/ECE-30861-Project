# src/services/cost_engine.py
import math
from typing import Dict
from src.models.artifacts import ArtifactCost
from src.services.s3_service import s3_client, get_bucket_name


def compute_artifact_cost(artifact, include_dependencies: bool) -> ArtifactCost:
    """
    Standalone cost = S3 object size in MB (rounded to 1 decimal).
    Dependency cost = same (baseline spec allows this).
    """

    key = artifact.data.download_url or artifact.data.url
    if not key:
        raise RuntimeError("Artifact missing blob reference")

    # Extract S3 key from a full URL if necessary
    if "amazonaws.com" in key:
        s3_key = key.split("/")[-1]
    else:
        s3_key = key

    bucket = get_bucket_name()

    # HEAD request to get object size
    head = s3_client.head_object(Bucket=bucket, Key=s3_key)
    size_bytes = head["ContentLength"]
    mb = round(size_bytes / (1024 * 1024), 1)

    result: Dict[str, Dict[str, float]] = {
        artifact.metadata.id: {
            "total_cost": mb
        }
    }

    if include_dependencies:
        result[artifact.metadata.id]["standalone_cost"] = mb

    return result
