from base import MetricBase
import time
import requests
from utils.huggingface_api import extract_model_or_dataset_id
from utils.tools import clamp


class DataQualityMetric(MetricBase):
    def __init__(self) -> None:
        super().__init__("data_quality")

    # -------------------------
    # Internal scoring helpers
    # -------------------------
    def _score_description(self, description: str) -> float:
        if not description:
            return 0.0
        length = len(description.strip())
        if length < 50:
            return 0.3
        elif length < 200:
            return 0.6
        return 1.0

    def _score_features(self, features: dict) -> float:
        if not features:
            return 0.0
        num_features = len(features)
        if num_features == 0:
            return 0.0
        elif num_features < 3:
            return 0.5
        return 1.0

    def _score_contributors(self, siblings: list) -> float:
        if not siblings:
            return 0.0
        if len(siblings) == 1:
            return 0.5
        return 1.0

    def _score_license(self, license: str) -> float:
        return 1.0 if license else 0.0

    # -------------------------
    # API Fetch
    # -------------------------
    def get_metadata_and_latency(self, url: str):
        dataset_id = extract_model_or_dataset_id(url)
        api_url = f"https://huggingface.co/api/datasets/{dataset_id}"

        try:
            start = time.time()
            response = requests.get(api_url)
            response.raise_for_status()
            latency = (time.time() - start) * 1000  # ms
            data = response.json()
            return data, latency
        except requests.HTTPError as e:
            print(f"API request failed for {dataset_id}: {e}")
            return None, None

    # -------------------------
    # Compute Quality Score
    # -------------------------
    def compute(self, url: str) -> float | None:
        print(f"\nComputing data quality metric for: {url}")
        data, latency = self.get_metadata_and_latency(url)

        if not data:
            print(f"Invalid or missing metadata for {url}")
            return None

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

        overall_score = clamp(overall_score)

        print(
            f"Description: {description_score}, Features: {features_score}, "
            f"Contributors: {contributors_score}, License: {license_score}"
        )
        print(f"Overall Quality Score: {overall_score:.4f}, Latency: {latency:.2f} ms")

        return overall_score, latency


# -------------------------
# Example Usage
# -------------------------
if __name__ == "__main__":
    url = "https://huggingface.co/datasets/squad"
    metric = DataQualityMetric()
    score, latency = metric.compute(url)

    if score is not None:
        print(f"Data Quality score for {url}: {score:.4f}, latency: {latency:.2f} ms")
    else:
        print(f"Could not compute data quality score for {url}")