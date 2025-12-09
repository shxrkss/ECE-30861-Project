# src/services/s3_service.py
import os
import re
import json
import boto3
from typing import List, Dict, Optional
from botocore.exceptions import ClientError
from datetime import datetime

S3_BUCKET = os.getenv("AWS_BUCKET_NAME")
if not S3_BUCKET:
    raise RuntimeError("AWS_BUCKET_NAME must be set in environment")

s3_client = boto3.client("s3")

def upload_file_to_s3(local_path: str, key: str, checksum: str = None) -> bool:
    extra_args = {"ServerSideEncryption": "AES256"}
    if checksum:
        extra_args["Metadata"] = {"checksum": checksum}
    try:
        s3_client.upload_file(local_path, S3_BUCKET, key, ExtraArgs=extra_args)
        return True
    except ClientError as e:
        print(f"S3 upload error → {e}")
        raise

def get_s3_object_checksum(key: str) -> Optional[str]:
    try:
        head = s3_client.head_object(Bucket=S3_BUCKET, Key=key)
        meta = head.get("Metadata", {})
        chk = meta.get("checksum")
        if chk:
            return chk
        etag = head.get("ETag", "").strip('"')
        return etag if etag else None
    except ClientError:
        return None

def generate_presigned_download_url(key: str, expires_in: int = 300) -> Optional[str]:
    try:
        return s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": key},
            ExpiresIn=expires_in,
        )
    except ClientError:
        return None

# -- Manifest support ----------------------------------------------------------------
def _manifest_key_for_model_key(model_key: str) -> str:
    # e.g. models/xyz.zip -> models/xyz/manifest.json
    base = model_key[:-4] if model_key.endswith(".zip") else model_key
    return f"{base}/manifest.json"

def write_manifest(model_key: str, manifest: Dict) -> bool:
    """Write manifest JSON next to model and set server-side encryption."""
    key = _manifest_key_for_model_key(model_key)
    js = json.dumps(manifest).encode("utf-8")
    try:
        s3_client.put_object(Bucket=S3_BUCKET, Key=key, Body=js, ServerSideEncryption="AES256")
        return True
    except ClientError as e:
        print(f"Error writing manifest: {e}")
        raise

def read_manifest(model_key: str) -> Optional[Dict]:
    key = _manifest_key_for_model_key(model_key)
    try:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        content = obj["Body"].read().decode("utf-8")
        return json.loads(content)
    except ClientError:
        return None

# The previous listing & search functions (unchanged)
def list_s3_models(prefix: str = "models/") -> List[Dict]:
    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix)
    results = []
    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".zip"):
                results.append({
                    "name": key.split("/")[-1].replace(".zip", ""),
                    "key": key,
                    "size": obj["Size"],
                    "last_modified": str(obj["LastModified"]),
                })
    return results

def get_model_card_text(model_key: str) -> str:
    possible_keys = [
        model_key.replace(".zip", "/README.md"),
        model_key.replace(".zip", "/metadata.json"),
    ]
    for key in possible_keys:
        try:
            obj = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
            return obj["Body"].read().decode("utf-8", errors="ignore")
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchKey":
                raise
    return ""

def search_models_by_card(all_models: List[Dict], regex: str) -> List[Dict]:
    import re as _re
    pattern = _re.compile(regex, _re.IGNORECASE)
    matched = []
    for model in all_models:
        try:
            text = get_model_card_text(model["key"])
            if pattern.search(text):
                matched.append(model)
        except Exception:
            continue
    return matched

def delete_prefix(prefix: str = "models/") -> int:
    """
    Delete all S3 objects under the given prefix.
    Returns the number of deleted objects.
    """
    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix)
    to_delete = []

    for page in pages:
        for obj in page.get("Contents", []):
            to_delete.append({"Key": obj["Key"]})

    if not to_delete:
        return 0

    # S3 delete_objects supports up to 1000 keys per call
    deleted_count = 0
    for i in range(0, len(to_delete), 1000):
        chunk = to_delete[i : i + 1000]
        resp = s3_client.delete_objects(
            Bucket=S3_BUCKET,
            Delete={"Objects": chunk},
        )
        deleted_count += len(resp.get("Deleted", []))

    return deleted_count
