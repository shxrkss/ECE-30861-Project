from base import MetricBase
import math
from urllib.parse import urlparse
import requests
import time
from utils.huggingface_api import extract_model_or_dataset_id
from utils.tools import clamp

# THIS METRIC HAS BEEN COMPLETED

class RampMetric(MetricBase):
    def __init__(self) -> None:
        super().__init__("ramp_up")


    # -------------------
    # Accesses API from url and gets the number of downloads for the specified model
    # -------------------
    def get_downloads_and_latency(self, url: str):
        
        parsed_url = urlparse(url)
        id_ = extract_model_or_dataset_id(url)

        if 'datasets' in parsed_url.netloc or parsed_url.path.startswith('/datasets'):
            api_url = f"https://huggingface.co/api/datasets/{id_}"
        else:
            api_url = f"https://huggingface.co/api/models/{id_}"

        try:
            start = time.time()
            response = requests.get(api_url)
            response.raise_for_status()
            latency = (time.time() - start) * 1000  # Calculates latencey converting seconds to milliseconds
            data = response.json()
            return data.get("downloads", 0), latency 
        
        except requests.HTTPError as e:
            print(f"API request failed for {id_}: {e}")
            return None, None


    # -------------------
    # Computes the ramp-up score based on number of downloads relative to other models
    # -------------------
    def compute(self, url: str) -> float | None:

        # Grab the number of downloads for the model and record the latency
        print(f"\nComputing ramp metric for: {url}")
        downloads, latency = self.get_downloads_and_latency(url)

        # Deal with invalid inputs and handle requests.HTTPError
        if downloads is None or downloads <= 0:
            print(f"Invalid or missing downloads count for {url}")
            return None

        # Actual calculation for the ramp-up score
        ramp_score = clamp((math.log(downloads) - 5) / 10)

        print(f"Downloads: {downloads}, Latency: {latency:.2f} ms")
        return ramp_score, latency


# -------------------
# Example code snippet that shows how to use the ramp-up metric
# -------------------
if __name__ == "__main__":
    url = "https://huggingface.co/LLM360/K2-Think"
    metric = RampMetric()
    ramp_score, latency = metric.compute(url)

    if ramp_score is not None:
        print(f"Ramp score for {url}: {ramp_score:.4f}, with latency of {latency:.2f} ms")
    else:
        print(f"Could not compute ramp up score for {url}")
