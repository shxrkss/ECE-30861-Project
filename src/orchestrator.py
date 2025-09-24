import concurrent.futures
import time
from typing import Dict, Tuple

# Import metric classes -> each new metric needs to be imported here
from metrics.bus_metric import BusMetric
from metrics.code_quality_metric import CodeQualityMetric
from metrics.dataset_quality_metric import DataQualityMetric
from metrics.dataset_code_score_metric import DatasetCodeMetric
from metrics.license_metric import LicenseMetric
from metrics.license_metric import LicenseMetric
from metrics.performance_metric import PerformanceMetric
from metrics.ramp_metric import RampMetric
from metrics.size_metric import SizeMetric

def run_all_metrics(repo_info: Tuple[str, str, str]) -> Dict[str, float]:
    """
    Orchestrates metric execution.
    repo_info = (code_url, dataset_url, model_url)

    Returns:
        dict of metric_name -> score/latency
    """

    code_url, dataset_url, model_url = repo_info
    results: Dict[str, float] = {}

    
