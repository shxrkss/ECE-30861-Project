from base import MetricBase
from utils.huggingface_api import get_repo_commits
from typing import Dict, Tuple
import time
import requests
from urllib.parse import urlparse

class PerformanceMetric(MetricBase):
    def __init__(self) -> None:
        super().__init__("performance")

    # ----------
    # 
    # ----------
    

    # -------------------
    # Computes the performance score
    # -------------------
    def compute(self, url: str) -> Tuple[float, float]:

        performance = -1
        latency = -1

        return performance, latency


# -------------------
# Example code snippet that shows how to use the bus metric
# -------------------
if __name__ == "__main__":
    url = "https://github.com/google-research/bert"
    metric = PerformanceMetric()
    performance, latency = metric.compute(url)
    
    if performance is not None:
        print(f"Performance score for {url}: {performance:.4f}, with latency of {latency:.2f} ms")
    else:
        print(f"Could not compute performance score for {url}")
