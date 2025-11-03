import boto3
import os
import re
from botocore.exceptions import ClientError
from typing import List, Dict

s3_client = boto3.client('s3')
S3_BUCKET = os.getenv("AWS_BUCKET_NAME", "bss-model-registry")

def list_s3_models() -> List[Dict]:
    """List all model files in the S3 bucket under /models."""
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=S3_BUCKET, Prefix="models/")

    models = []
    for page in pages:
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.zip'):
                models.append({
                    "name": obj['Key'].split('/')[-1].replace(".zip", ""),
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": str(obj['LastModified'])
                })
    return models


def get_model_card_text(model_key: str) -> str:
    """Fetch model card text (README.md or metadata.json) from S3 if available."""
    for possible_key in [
        model_key.replace(".zip", "/README.md"),
        model_key.replace(".zip", "/metadata.json"),
    ]:
        try:
            obj = s3_client.get_object(Bucket=S3_BUCKET, Key=possible_key)
            content = obj['Body'].read().decode('utf-8', errors='ignore')
            return content
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchKey':
                raise
    return ""


def search_models_by_card(all_models: List[Dict], regex: str) -> List[Dict]:
    """Filter models whose README or metadata contains the given regex."""
    pattern = re.compile(regex, re.IGNORECASE)
    matched = []

    for model in all_models:
        try:
            card_text = get_model_card_text(model['key'])
            if pattern.search(card_text):
                matched.append(model)
        except Exception as e:
            print(f"Skipping {model['name']} due to error: {e}")

    return matched