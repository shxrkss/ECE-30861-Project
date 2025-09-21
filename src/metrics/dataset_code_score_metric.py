from base import MetricBase
from utils.huggingface_api import get_repo_commits
from typing import Dict, Tuple
import time
import requests
from urllib.parse import urlparse

class DatasetCodeMetric(MetricBase):
    def __init__(self) -> None:
        super().__init__("dataset_code_score")

    # ----------
    # 
    # ----------
    

    # -------------------
    # Computes the code quality score
    # -------------------
    def compute(self, url: str) -> Tuple[float, float]:

        score = -1
        latency = -1

        return score, latency


# -------------------
# Example code snippet that shows how to use the bus metric
# -------------------
if __name__ == "__main__":
    url = "https://github.com/google-research/bert"
    metric = DatasetCodeMetric()
    score, latency = metric.compute(url)
    
    if score is not None:
        print(f"Dataset and Code Score for {url}: {score:.4f}, with latency of {latency:.2f} ms")
    else:
        print(f"Could not compute dataset and code score for {url}")
