# NOTE: If testing this file directly, ensure to add "src." before "metrics.base"
from metrics.base import MetricBase
from huggingface_hub import HfApi
from typing import Dict, Tuple
import time
from urllib.parse import urlparse
import math

# THIS METRIC HAS BEEN COMPLETED
# if needed, can implement huggingface api token with: HF_API_TOKEN

class BusMetric(MetricBase):
    def __init__(self) -> None:
        super().__init__("bus_factor")
        self.hf = HfApi()

    # -------------------
    # Gets contributor statistics from a HuggingFace model repository
    # -------------------
    def get_hf_contributor_stats(self, repo_url: str) -> Tuple[int, int, Dict[str, int]]:
        ''' Returns (N, C, ci) where:
            N = number of unique contributors
            C = total number of contributions (commits)
            ci = dictionary mapping contributor to their number of contributions
        '''

        # parse owner / repo from HF model URL
        parsed_parts = urlparse(repo_url).path.strip('/').split('/')
        if len(parsed_parts) < 2:
            return {}
        repo_id = f"{parsed_parts[0]}/{parsed_parts[1]}"

        ci: Dict[str, int] = {}
        total = 0

        # This returns a list of CommitInfo objects
        try:
            commits = self.hf.list_repo_commits(repo_id=repo_id)
        except Exception as e:
            return 0, 0, {}

        for c in commits:
            for author in c.authors:
                ci[author] = ci.get(author, 0) + 1
                total += 1

        N = len(ci)

        return N, total, ci
    
    # -------------------
    # Computes the bus metric using contributor information
    # -------------------
    def compute(self, url: str) -> Tuple[float, float]:
        if url is None:
            return 0, 0

        start = time.time()
        N, C, ci = self.get_hf_contributor_stats(url)

        if N <= 1 or C == 0:
            end = time.time()
            latency = (end - start) * 1000
            latency = int(latency)
            return 0.0, latency

        # Calculate entropy based bus factor
        # previous implementation penalized heavy contributors too much
        # Entropy based is more balanced as it considers distribution of contributions
        # Implementation formula was inspired by: an llm
        entropy = 0.0
        for contributions in ci.values():
            p = contributions / C
            entropy -= p * math.log2(p)

        max_entropy = math.log2(N)
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

        latency = int((time.time() - start) * 1000)

        return normalized_entropy, latency



# -------------------
# Example code snippet that shows how to use the bus metric
# -------------------
if __name__ == "__main__":
    url = "https://huggingface.co/google-bert/bert-base-uncased"
    metric = BusMetric()
    bus_factor, latency = metric.compute(url)
    
    if bus_factor is not None:
        print(f"Bus factor for {url}: {bus_factor:.4f}, with latency of {latency} ms")
    else:
        print(f"Could not compute bus factor for {url}")
