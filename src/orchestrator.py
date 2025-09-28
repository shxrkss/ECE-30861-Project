from concurrent.futures import ThreadPoolExecutor
import time
import sys
from typing import Dict, Tuple

def run_all_metrics(repo_info: Tuple[str, str, str]) -> Dict[str, float]:
    """
    Orchestrates metric execution.
    repo_info = (code_url, dataset_url, model_url)

    Returns:
        A dictionary with all metric results.
    """

    start = time.time()

    # Import metric classes -> each new metric needs to be imported here
    from metrics.bus_metric import BusMetric
    from metrics.code_quality_metric import CodeQualityMetric
    from metrics.dataset_quality_metric import DataQualityMetric

    code_url, dataset_url, model_url = repo_info

    bus_score, bus_latency = None, None
    code_score, code_latency = None, None
    data_score, data_latency = None, None

    def run_bus():
        nonlocal bus_score, bus_latency
        bus_score, bus_latency = BusMetric().compute(model_url)

    def run_code():
        nonlocal code_score, code_latency
        code_score, code_latency = CodeQualityMetric().compute(code_url, model_url)

    def run_data():
        nonlocal data_score, data_latency
        data_score, data_latency = DataQualityMetric().compute(dataset_url)

    
    with ThreadPoolExecutor(max_workers=3) as executor:
        executor.submit(run_bus)
        executor.submit(run_code)
        executor.submit(run_data)

    end = time.time()
    net_latency = (end - start) * 1000
    net_latency = int(net_latency)

    return {
        "net_score": 0.95,
        "net_score_latency": net_latency,
        "ramp_up_time": 0.90,
        "ramp_up_time_latency": 45,
        "bus_factor": round(bus_score, 4),
        "bus_factor_latency": int(bus_latency),
        "performance_claims": 0.92,
        "performance_claims_latency": 35,
        "license": 1.00,
        "license_latency": 10,
        "size_score": {
            "raspberry_pi": 0.20,
            "jetson_nano": 0.40,
            "desktop_pc": 0.95,
            "aws_server": 1.00
        },
        "size_score_latency": 50,
        "dataset_and_code_score": 1.00,
        "dataset_and_code_score_latency": 15,
        "dataset_quality": data_score,
        "dataset_quality_latency": int(data_latency),
        "code_quality": code_score,
        "code_quality_latency": int(code_latency)
    }


