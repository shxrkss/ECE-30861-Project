import boto3
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError
import logging

load_dotenv()
logger = logging.getLogger(__name__)

AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("AWS_S3_BUCKET")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=AWS_REGION
)

def upload_file_to_s3(file_path: str, s3_key: str) -> bool:
    """Upload a local file to S3 under the given key."""
    try:
        s3_client.upload_file(file_path, S3_BUCKET, s3_key)
        logger.info(f"Uploaded {file_path} to s3://{S3_BUCKET}/{s3_key}")
        return True
    except ClientError as e:
        logger.error(f"S3 upload failed: {e}")
        return False
