import time
import logging
import requests
from metrics.base import MetricBase

class LicenseCheckMetric(MetricBase):
    """
    Compares model and GitHub repository licenses for fine-tune/inference compatibility.
    """

    def __init__(self):
        super().__init__("license_check")

    def classify_license(self, name: str) -> str:
        if not name:
            return "unknown"
        name = name.lower()
        if any(x in name for x in ["mit", "bsd", "apache", "mpl"]):
            return "permissive"
        if "gpl" in name:
            return "copyleft"
        if "cc-by-nc" in name or "proprietary" in name:
            return "restricted"
        return "unknown"

    def compatible(self, model_type: str, repo_type: str) -> float:
        if repo_type == "permissive":
            return 1.0
        if repo_type == "copyleft" and model_type == "permissive":
            return 0.5
        return 0.0

    def compute(self, github_url: str, model_license: str) -> tuple[float, int]:
        start = time.time()
        try:
            owner, repo = github_url.rstrip("/").split("/")[-2:]
            res = requests.get(f"https://api.github.com/repos/{owner}/{repo}/license")
            data = res.json()
            repo_license = data.get("license", {}).get("spdx_id", "")

            repo_class = self.classify_license(repo_license)
            model_class = self.classify_license(model_license)
            score = self.compatible(model_class, repo_class)

            latency = int((time.time() - start) * 1000)
            logging.info(f"[LicenseCheck] Model={model_class}, Repo={repo_class}, Score={score}")
            return score, latency
        except Exception as e:
            logging.error(f"[LicenseCheck] Failed: {e}")
            return -1, 0