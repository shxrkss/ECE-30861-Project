import time
import requests
from typing import Tuple
from metrics.base import MetricBase
from metrics.utils.huggingface_api import extract_model_or_dataset_id
from metrics.utils.tools import clamp
from typing import Optional, Dict, Any

# ALL PRINT STATEMENTS NEED TO GO TO LOGGING

class DataQualityMetric(MetricBase):
    def __init__(self) -> None:
        super().__init__("data_quality")

    # -------------------------
    # Internal scoring helpers
    # -------------------------
    def _score_description(self, description: str) -> float:
        """Scores description length."""

        if not description:
            return 0.2
        length = len(description.strip())
        if length < 50:
            return 0.3
        elif length < 200:
            return 0.6
        return 1.0

    def _score_features(self, features: dict) -> float:
        """Scores based on number of features."""

        if not features:
            return 0.2
        num_features = len(features)
        if num_features == 0:
            return 0.0
        elif num_features < 3:
            return 0.5
        return 1.0

    def _score_contributors(self, siblings: list) -> float:
        """Scores based on number of contributors."""

        if not siblings:
            return 0.2
        if len(siblings) == 1:
            return 0.5
        return 1.0

    def _score_license(self, license: str) -> float:
        """Scores based on presence of license."""

        return 1.0 if license else 0.2

    # -------------------------
    # API Fetch
    # -------------------------
    def get_metadata_and_latency(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetches dataset metadata from HuggingFace API.
            args:
                url: HuggingFace dataset URL
            returns:
                dict with metadata if successful, else None
        """
        dataset_id = extract_model_or_dataset_id(url)

        if dataset_id.startswith("datasets/"):
            dataset_id = dataset_id[len("datasets/"):]
        api_url = f"https://huggingface.co/api/datasets/{dataset_id}"

        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.HTTPError as e:
            print(f"API request failed for {dataset_id}: {e}")
            return None, None

    # -------------------------
    # Compute Quality Score
    # -------------------------
    def compute(self, url: str) -> Tuple[float, int]:
        """Computes the data quality score for a given HuggingFace dataset URL.

            Args:
                url: Hugging Face dataset URL

            Returns tuple:
                data_quality_score: A float between 0 and 1 representing the data quality
                latency: Time taken to compute the metric in milliseconds
        """
        
        start = time.time()

        if self.is_applicable(url) is False:
            # print(f"DataQualityMetric not applicable for URL: {url}")
            return 0.0, 0
        
        data = self.get_metadata_and_latency(url)

        if not data:
            print(f"Invalid or missing metadata for {url}")
            return 0.0, 0

        card_data = data.get("cardData", {}) or {}

        description_score = self._score_description(card_data.get("description", ""))
        features_score = self._score_features(card_data.get("features", {}))
        contributors_score = self._score_contributors(data.get("siblings", []))
        license_score = self._score_license(
            card_data.get("license") or card_data.get("licenses", "")
        )

        overall_score = (
            description_score + features_score + contributors_score + license_score
        ) / 4

        card_bonus = 0.1 if card_data else 0.0
        overall_score = clamp(overall_score + card_bonus)

        end = time.time()
        latency = (end - start) * 1000  # convert to milliseconds
        latency = int(latency)

        return overall_score, latency

    def is_applicable(self, url: Optional[str]) -> bool:
        if url is None:
            return False
        return True

# -------------------------
# Example Usage
# -------------------------
if __name__ == "__main__":
    url = "https://huggingface.co/datasets/bookcorpus/bookcorpus"
    metric = DataQualityMetric()
    score, latency = metric.compute(url)

    if score is not None:
        print(f"Data Quality score for {url}: {score:.4f}, latency: {latency:.2f} ms")
    else:
        print(f"Could not compute data quality score for {url}")