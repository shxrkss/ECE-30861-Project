from base import MetricBase
from utils.huggingface_api import get_repo_commits
from typing import Dict, Tuple
import time
import requests
from urllib.parse import urlparse

class LicenseMetric(MetricBase):
    def __init__(self) -> None:
        super().__init__("license")

    # ----------
    # 
    # ----------
    

    # -------------------
    # Computes the license score
    # -------------------
    def compute(self, url: str) -> Tuple[float, float]:

        license = -1
        latency = -1

        return license, latency


# -------------------
# Example code snippet that shows how to use the bus metric
# -------------------
if __name__ == "__main__":
    url = "https://github.com/google-research/bert"
    metric = LicenseMetric()
    license, latency = metric.compute(url)
    
    if license is not None:
        print(f"License score for {url}: {license:.4f}, with latency of {latency:.2f} ms")
    else:
        print(f"Could not compute license score for {url}")
