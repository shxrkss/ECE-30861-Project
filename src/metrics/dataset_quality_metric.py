import time
import logging
import requests
from typing import Tuple, Optional, Dict, Any
from urllib.parse import urlparse
import os

from base import MetricBase
from utils.tools import clamp

log = logging.getLogger(__name__)

HF_API_BASE = "https://huggingface.co"

def _parse_hf_url(url: str) -> Tuple[str, str]:
    """
    Returns (repo_id, repo_type) where repo_type ∈ {'dataset','model','space'}.
    """
    p = urlparse(url)
    parts = [s for s in p.path.split("/") if s]
    if not parts:
        raise ValueError(f"Invalid HF URL: {url}")
    head = parts[0].lower()
    if head in ("datasets", "dataset"):
        return "/".join(parts[1:3]), "dataset"
    if head in ("spaces", "space"):
        return "/".join(parts[1:3]), "space"
    # default: model
    return (parts[0] if len(parts) == 1 else "/".join(parts[:2])), "model"


class DataQualityMetric(MetricBase):
    def __init__(self) -> None:
        super().__init__("data_quality")

    # -------------------------
    # Internal scoring helpers
    # -------------------------
    def _score_description(self, description: str) -> float:
        if not description:
            return 0.2
        length = len(description.strip())
        if length < 50:
            return 0.3
        elif length < 200:
            return 0.6
        return 1.0

    def _score_features(self, features: Any) -> float:
        """
        features can be dict/list/str depending on the dataset card.
        """
        if not features:
            return 0.2
        if isinstance(features, dict):
            num = len(features)
        elif isinstance(features, list):
            num = len(features)
        elif isinstance(features, str):
            # crude heuristic: count commas/newlines as proxies
            num = max(features.count(",") + 1, features.count("\n"))
        else:
            num = 0
        if num == 0:
            return 0.0
        elif num < 3:
            return 0.5
        return 1.0

    def _score_contributors(self, siblings: Any) -> float:
        if not siblings:
            return 0.2
        try:
            n = len(siblings)
        except Exception:
            n = 0
        if n <= 1:
            return 0.5 if n == 1 else 0.2
        return 1.0

    def _score_license(self, license_value: Any) -> float:
        """
        license can be string, list, or dict in cardData.
        """
        if not license_value:
            return 0.2
        if isinstance(license_value, str):
            return 1.0
        if isinstance(license_value, (list, dict)):
            return 1.0 if len(license_value) > 0 else 0.2
        return 0.6

    # -------------------------
    # API Fetch (datasets only)
    # -------------------------
    def _get_dataset_metadata(self, repo_id: str, hf_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Hit the public HF REST endpoint for datasets. Returns dict or None.
        """
        url = f"{HF_API_BASE}/api/datasets/{repo_id}"
        headers = {"Accept": "application/json"}
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"

        try:
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.HTTPError as e:
            log.warning("HF datasets API failed for %s: %s", repo_id, e)
            return None
        except Exception as e:
            log.exception("Unexpected error fetching dataset metadata for %s: %s", repo_id, e)
            return None

    # -------------------------
    # Compute Quality Score
    # -------------------------
    def compute(self, url: str, hf_token: Optional[str] = None) -> Tuple[float, int]:
        """
        Computes data quality score for a Hugging Face **dataset** URL.

        Returns:
          (score in [0,1], latency_ms)
        """
        start = time.time()

        if not url:
            return 0.0, 0

        repo_id, repo_type = _parse_hf_url(url)
        if repo_type != "dataset":
            # Not a dataset -> not applicable
            log.info("DataQualityMetric not applicable for non-dataset URL: %s (type=%s)", url, repo_type)
            latency = int((time.time() - start) * 1000)
            return 0.0, latency

        data = self._get_dataset_metadata(repo_id, hf_token=hf_token)
        if not data:
            log.warning("Invalid or missing dataset metadata for %s", url)
            latency = int((time.time() - start) * 1000)
            return 0.0, latency

        card_data = data.get("cardData") or {}

        description_score  = self._score_description(card_data.get("description", ""))
        features_score     = self._score_features(card_data.get("features", {}))
        contributors_score = self._score_contributors(data.get("siblings", []))
        license_score      = self._score_license(card_data.get("license") or card_data.get("licenses"))

        overall = (description_score + features_score + contributors_score + license_score) / 4.0
        card_bonus = 0.1 if card_data else 0.0
        overall = clamp(overall + card_bonus)

        latency = int((time.time() - start) * 1000)
        return overall, latency

    def is_applicable(self, url: Optional[str]) -> bool:
        return bool(url)

# -------------------------
# Example Usage
# -------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    metric = DataQualityMetric()

    # Use a **dataset** URL here (not a model URL):
    for url in [
        "https://huggingface.co/datasets/squad",
        "https://huggingface.co/datasets/glue",
        # "https://huggingface.co/openai/whisper-tiny",  # <-- this is a MODEL, not a dataset; will return 0.0 (not applicable)
    ]:
        score, latency = metric.compute(url, hf_token=os.getenv("HF_TOKEN"))  # HF_TOKEN only needed for gated/private datasets
        print(f"{url} -> score={score:.3f} latency={latency}ms")
