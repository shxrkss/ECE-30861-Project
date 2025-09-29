# data_and_code_quality_metric.py
from __future__ import annotations
import os
from typing import Optional, Tuple
from urllib.parse import urlparse

from metrics.base import MetricBase
from metrics.utils.tools import clamp
from metrics.dataset_quality_metric import DataQualityMetric
from metrics.code_quality_metric import CodeQualityMetric

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

DATA_WEIGHT = 0.6
CODE_WEIGHT = 0.4

def _repo_type(url: str) -> str:
    p = urlparse(url)
    parts = [s for s in p.path.split("/") if s]
    if not parts: return "model"
    head = parts[0].lower()
    if head in ("datasets", "dataset"): return "dataset"
    if head in ("spaces", "space"):     return "space"
    return "model"

def _unwrap_score(v) -> Optional[float]:
    if v is None: return None
    if isinstance(v, tuple) and len(v) >= 1:
        return float(v[0])
    if isinstance(v, (int, float)):
        return float(v)
    return None

def _call_metric(metric_obj, url: str, hf_token: Optional[str]) -> Optional[float]:
    """
    Call metric.compute(...) in a way that’s compatible with both signatures:
      compute(url)                -> float or (float, latency)
      compute(url, hf_token=...)  -> float or (float, latency)
    """
    # Try with hf_token first
    if hf_token is not None:
        try:
            return _unwrap_score(metric_obj.compute(url, hf_token=hf_token))
        except TypeError:
            pass  # metric doesn't accept hf_token
    # Fallback: call without hf_token
    return _unwrap_score(metric_obj.compute(url))

class DataAndCodeQualityMetric(MetricBase):
    def __init__(self):
        super().__init__("data_and_code_quality")
        self.data_metric = DataQualityMetric()
        self.code_metric = CodeQualityMetric()

    def compute(self, url: str, hf_token: Optional[str] = None) -> float:
        rtype = _repo_type(url)

        scores = []
        weights = []

        # Use dataset metric only for dataset repos
        if rtype == "dataset":
            ds_score = _call_metric(self.data_metric, url, hf_token)
            if ds_score is not None:
                scores.append(ds_score)
                weights.append(DATA_WEIGHT)

        # Code metric may apply to models/datasets/spaces depending on your implementation
        cq_score = _call_metric(self.code_metric, url, hf_token)
        if cq_score is not None:
            scores.append(cq_score)
            weights.append(CODE_WEIGHT)

        if not weights:
            return 0.0

        wsum = sum(weights)
        combined = sum(s * (w / wsum) for s, w in zip(scores, weights))
        return clamp(combined)

if __name__ == "__main__":
    metric = DataAndCodeQualityMetric()
    for url in [
        "https://huggingface.co/datasets/squad",          # dataset
        "https://huggingface.co/openai/whisper-tiny",     # model
    ]:
        s = metric.compute(url, hf_token=os.getenv("HF_TOKEN"))
        print(f"{url} -> {s:.4f}")
