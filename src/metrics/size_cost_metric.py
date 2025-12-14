import os
import time
import math
import logging
from metrics.base import MetricBase
from huggingface_hub import HfApi
import boto3
from botocore.exceptions import ClientError


class SizeCostMetric(MetricBase):
    """
    Computes a 'size cost' metric for models based on their total file size.
    Supports both Hugging Face and S3-hosted models.
    """

    def __init__(self):
        super().__init__("size_cost")
        self.hf = HfApi()
        self.s3 = boto3.client("s3")

    def _get_hf_size(self, model_id: str) -> float:
        total = 0
        try:
            files = self.hf.list_repo_files(model_id)
            for f in files:
                info = self.hf.model_info(model_id)
                # HF Hub doesn’t expose file-by-file size easily — fallback to total
                total = info.safetensors.get("total", 0) or info.model_card_data.get("file_size", 0)
            return total / (1024 * 1024)
        except Exception as e:
            logging.error(f"[SizeCostMetric] Failed to get Hugging Face size: {e}")
            return 0

    def _get_s3_size(self, bucket: str, prefix: str) -> float:
        total_bytes = 0
        try:
            response = self.s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            for obj in response.get("Contents", []):
                total_bytes += obj["Size"]
            return total_bytes / (1024 * 1024)
        except ClientError as e:
            logging.error(f"[SizeCostMetric] Failed to get S3 size: {e}")
            return 0

    def compute(self, url: str) -> tuple[float, int]:
        start = time.time()
        size_mb = 0

        try:
            if "huggingface.co" in url:
                model_id = "/".join(url.strip("/").split("/")[-2:])
                size_mb = self._get_hf_size(model_id)
            elif "s3://" in url:
                s3_parts = url.replace("s3://", "").split("/", 1)
                bucket, prefix = s3_parts[0], s3_parts[1] if len(s3_parts) > 1 else ""
                size_mb = self._get_s3_size(bucket, prefix)
            else:
                logging.warning(f"[SizeCostMetric] Unknown URL format: {url}")

            score = 1 / (1 + math.log1p(size_mb)) if size_mb > 0 else 0
            latency = int((time.time() - start) * 1000)
            logging.info(f"[SizeCostMetric] Computed size={size_mb:.2f}MB, score={score:.3f}")
            return score, latency

        except Exception as e:
            logging.error(f"[SizeCostMetric] Error computing size cost: {e}")
            return 0, 0