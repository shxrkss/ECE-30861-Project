from base import MetricBase
from utils.huggingface_api import get_repo_commits
from typing import Dict, Tuple
import time
import requests
from urllib.parse import urlparse

class CodeQualityMetric(MetricBase):
    def __init__(self) -> None:
        super().__init__("code_quality")

    # ----------
    # 
    # ----------
    

    # -------------------
    # Computes the code quality score
    # -------------------
    def compute(self, url: str) -> Tuple[float, float]:

        quality = -1
        latency = -1

        return quality, latency


# -------------------
# Example code snippet that shows how to use the bus metric
# -------------------
if __name__ == "__main__":
    url = "https://github.com/google-research/bert"
    metric = CodeQualityMetric()
    quality, latency = metric.compute(url)
    
    if quality is not None:
        print(f"Code quality score for {url}: {quality:.4f}, with latency of {latency:.2f} ms")
    else:
        print(f"Could not compute code quality for {url}")
