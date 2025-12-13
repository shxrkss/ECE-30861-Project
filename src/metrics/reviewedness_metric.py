import time
import logging
import requests
import re
import sys
import os
from urllib.parse import urlparse
from huggingface_hub import HfApi
from src.metrics.base import MetricBase
from ..log import setup_logging

# Optional: GitHub token for higher API rate limits
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", None)
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

class ReviewednessMetric(MetricBase):
    """
    Computes the Reviewedness metric:
    Fraction of code (not weights) introduced through PRs that had reviews.
    """

    def __init__(self):
        super().__init__("reviewedness")
        self.hf = HfApi()

    # -------------------
    # Helper: extract GitHub repo from HF model metadata
    # -------------------
    def extract_github_repo(self, url: str) -> str:
        try:
            model_info = self.hf.model_info(urlparse(url).path.strip("/"))
            if model_info and model_info.cardData:
                text = model_info.cardData.get("text", "")
                match = re.search(r"https?://github\.com/([\w\-\_]+)/([\w\-\_\.]+)", text)
                if match:
                    return f"{match.group(1)}/{match.group(2)}"
        except Exception as e:
            logging.warning(f"Could not extract GitHub link: {e}")
        return ""

    # -------------------
    # Helper: fetch PRs and compute reviewed ratio
    # -------------------
    def get_reviewed_fraction(self, repo_id: str) -> float:
        owner, repo = repo_id.split("/")
        prs_url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=closed&per_page=50"

        try:
            prs = requests.get(prs_url, headers=HEADERS, timeout=10).json()
            if not isinstance(prs, list) or not prs:
                return 0.0

            total_lines = 0
            reviewed_lines = 0

            for pr in prs:
                if not pr.get("merged_at"):
                    continue  # skip unmerged PRs

                # count lines changed
                additions = pr.get("additions", 0)
                deletions = pr.get("deletions", 0)
                changes = additions + deletions
                total_lines += changes

                # fetch reviews for this PR
                review_url = pr.get("review_comments_url", "")
                if review_url:
                    reviews = requests.get(review_url, headers=HEADERS, timeout=5).json()
                    if isinstance(reviews, list) and len(reviews) > 0:
                        reviewed_lines += changes

            if total_lines == 0:
                return 0.0
            return reviewed_lines / total_lines

        except Exception as e:
            logging.error(f"Error accessing GitHub API: {e}")
            return 0.0

    # -------------------
    # Main compute function
    # -------------------
    def compute(self, url: str):
        setup_logging()
        start = time.time()
        logging.critical("Starting Reviewedness Metric")

        # Step 1: get GitHub repo link
        repo_id = self.extract_github_repo(url)
        if not repo_id:
            self.value = -1.0
            latency = int((time.time() - start) * 1000)
            return self.value, latency

        # Step 2: compute fraction of reviewed code
        self.value = self.get_reviewed_fraction(repo_id)
        latency = int((time.time() - start) * 1000)
        logging.info(f"Reviewedness metric for {repo_id}: {self.value:.3f}")
        return self.value, latency


# -------------------
# Example usage
# -------------------
if __name__ == "__main__":
    metric = ReviewednessMetric()
    test_url = "https://huggingface.co/google-bert/bert-base-uncased"
    score, latency = metric.compute(test_url)
    print(f"Reviewedness score: {score:.3f}, latency: {latency} ms")