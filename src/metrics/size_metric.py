from base import MetricBase
from utils.huggingface_api import get_repo_commits
from typing import Dict, Tuple
import time
import requests
from urllib.parse import urlparse

class SizeMetric(MetricBase):
    def __init__(self) -> None:
        super().__init__("size")

    # need to replace param with whatever is needed to compute size
    def compute(self, url, param) -> float:
        """Compute size metric using using calcuation"""

        size_score = -1#(math.log(param) - 15) / 10
        latency = -1

        return size_score, latency

# -------------------
# Example code snippet that shows how to use the bus metric
# -------------------
if __name__ == "__main__":
    url = "https://github.com/google-research/bert"
    metric = SizeMetric()
    size_score, latency = metric.compute(url)
    
    if size_score is not None:
        print(f"Size score for {url}: {size_score:.4f}, with latency of {latency:.2f} ms")
    else:
        print(f"Could not compute size score for {url}")

