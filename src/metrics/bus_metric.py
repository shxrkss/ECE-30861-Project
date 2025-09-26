from metrics.base import MetricBase
from metrics.utils.huggingface_api import get_repo_commits
from typing import Dict, Tuple
import time
import requests
from urllib.parse import urlparse

# THIS METRIC HAS BEEN COMPLETED

class BusMetric(MetricBase):
    def __init__(self) -> None:
        super().__init__("bus_factor")


    # ----------
    # Given a GitHub repo URL, returns:
    # - number of contributors (N)
    # - total contributions (C)
    # - contributions per contributor (ci: Dict[str, int])
    # ----------
    def get_github_contributor_stats(self, repo_url: str):

        # Parse owner and repo from the URL
        parsed = urlparse(repo_url)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) != 2:
            raise ValueError("Invalid GitHub repo URL format")

        owner, repo = path_parts
        api_url = f"https://api.github.com/repos/{owner}/{repo}/stats/contributors"

        # print(f"\nFetching contributor stats from: {api_url}")

        headers = {
            # Optional: add your GitHub token here to avoid rate limits
            # "Authorization": "Bearer YOUR_GITHUB_TOKEN"
        }

        response = requests.get(api_url, headers=headers)

        if response.status_code == 202:
            print("GitHub is generating statistics... try again in a few seconds.")
            return -1, -1, -1

        if not response.ok:
            raise Exception(f"GitHub API error: {response.status_code} {response.text}")

        data = response.json()

        ci = {}
        total_contributions = 0

        for contributor in data:
            username = contributor['author']['login']
            contributions = contributor['total']
            ci[username] = contributions
            total_contributions += contributions

        num_contributors = len(ci)

        return num_contributors, total_contributions, ci


    # -------------------
    # Computes the bus metric using contributor information
    # -------------------
    def compute(self, url: str) -> Tuple[float, float]:
        
        if url == None:
            return 0,0
        start: float = time.time()

        N: int # Number of contributors
        C: int # Total contributions
        ci: Dict[str, int] # Contributions per contributor
        N, C, ci = self.get_github_contributor_stats(url)

        if N <= 1 or C == 0:
            return 0.0, (time.time() - start) * 1000

        sum_of_squared_factors: float = 0.0
        for contributions in ci.values():
            sum_of_squared_factors += (contributions / C) ** 2

        bus_factor: float = (N * sum_of_squared_factors) / (N - 1)

        end: float = time.time()
        latency: float = (end - start) * 1000

        # print(f"Contributors: {N}, Total Contributions: {C}, Latency: {latency:.2f} ms")
        return bus_factor, latency


# -------------------
# Example code snippet that shows how to use the bus metric
# -------------------
if __name__ == "__main__":
    url = "https://github.com/google-research/bert"
    metric = BusMetric()
    bus_factor, latency = metric.compute(url)
    
    if bus_factor is not None:
        print(f"Bus factor for {url}: {bus_factor:.4f}, with latency of {latency:.2f} ms")
    else:
        print(f"Could not compute bus factor for {url}")
