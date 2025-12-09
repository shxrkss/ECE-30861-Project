# src/services/cost_engine.py
import math
from typing import Dict
from src.models.artifacts import ArtifactCost
from src.services.s3_service import s3_client, get_bucket_name

bucket = get_bucket_name()
s3_client.upload_file(path, bucket, key)


def compute_artifact_cost(artifact, include_dependencies: bool) -> ArtifactCost:
    """
    Standalone cost = S3 object size in MB (rounded to 1 decimal).
    Dependency cost = same (baseline spec allows this).
    """

    key = artifact.data.download_url or artifact.data.url
    if not key:
        raise RuntimeError("Artifact missing blob reference")

    # Bucket S3 key may be stored as full URL. Extract if necessary.
    if "amazonaws.com" in key:
        # key after last slash
        s3_key = key.split("/")[-1]
    else:
        s3_key = key

    # HEAD request
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
