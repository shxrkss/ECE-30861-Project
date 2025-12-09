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
    from metrics.license_metric import LicenseMetric
    from metrics.ramp_metric import RampMetric
    from metrics.size_metric import SizeMetric
    from metrics.performance_metric import PerformanceClaimMetricLLM
    
    from metrics.reproducibility_metric import ReproducibilityMetric
    from metrics.reviewedness_metric import ReviewednessMetric
    
    code_url, dataset_url, model_url = repo_info

    bus_score, bus_latency = None, None
    code_score, code_latency = None, None
    data_score, data_latency = None, None
    license_score, license_latency = None, None
    ramp_score, ramp_latency = None, None
    size_rpi, size_jetson, size_pc, size_aws, size_latency = None, None, None, None, None
    performance_score, performance_latency = None, None

    reproducibility_score, reproducibility_latency = None, None
    reviewedness_score, reviewedness_latency = None, None
    
    def run_bus():
        nonlocal bus_score, bus_latency
        bus_score, bus_latency = BusMetric().compute(model_url)

    def run_code():
        nonlocal code_score, code_latency
        code_score, code_latency = CodeQualityMetric().compute(code_url, model_url)

    def run_data():
        nonlocal data_score, data_latency
        data_score, data_latency = DataQualityMetric().compute(dataset_url)
    
    # EDIT ALLOWED LICENSES HERE
    def run_license():
        nonlocal license_score, license_latency
        allowed = {'mit', 'apache-2.0', 'bsd-3-clause', 'bsd-2-clause', 'gpl-3.0', 'lgpl-3.0', 'mpl-2.0'}
        license_score, license_latency = LicenseMetric().compute(model_url, allowed=allowed, hf_token=None)
    
    def run_ramp():
        nonlocal ramp_score, ramp_latency
        ramp_score, ramp_latency = RampMetric().compute(model_url)
    
    def run_size():
        nonlocal size_rpi, size_jetson, size_pc, size_aws, size_latency
        size_rpi, size_jetson, size_pc, size_aws, size_latency = SizeMetric().compute(model_url, hf_token=None)

    def run_performance():
        nonlocal performance_score, performance_latency
        performance_score, performance_latency = PerformanceClaimMetricLLM(debug=False).compute(model_url, hf_token=None)
    
    def run_reproducibility():
        nonlocal reproducibility_score, reproducibility_latency
        reproducibility_score, reproducibility_latency = ReproducibilityMetric().compute(model_url, hf_token = None)

    def run_reviewedness():
        nonlocal reviewedness_score, reviewedness_latency
        reviewedness_score, reviewedness_latency = ReviewednessMetric().compute(model_url)

    with ThreadPoolExecutor(max_workers=3) as executor:
        executor.submit(run_bus)
        executor.submit(run_code)
        executor.submit(run_data)
        executor.submit(run_license)
        executor.submit(run_ramp)
        executor.submit(run_size)
        executor.submit(run_performance)
        executor.submit(run_reproducibility)
        executor.submit(run_reviewedness)

    data_set_code_score = (code_score + data_score) / 2.0
    data_set_code_latency = (code_latency + data_latency) / 2

    end = time.time()

    net_score = (bus_score + code_score + data_score + ramp_score + license_score + performance_score) / 6
    net_latency = (end - start) * 1000
    net_latency = int(net_latency)

    return {
        "net_score": round(net_score, 2),
        "net_score_latency": net_latency,
        "ramp_up_time": round(ramp_score, 2),
        "ramp_up_time_latency": int(ramp_latency),
        "bus_factor": round(bus_score, 2),
        "bus_factor_latency": int(bus_latency),
        "performance_claims": round(performance_score, 2),
        "performance_claims_latency": int(performance_latency),
        "license": round(license_score, 2),
        "license_latency": license_latency,
        "size_score": {
            "raspberry_pi": 0.0,
            "jetson_nano": 0.0,
            "desktop_pc": 0.0,
            "aws_server": 0.0
        },
        "size_score_latency": 0,
        "size_score": {
            "raspberry_pi": round(size_rpi, 2),
            "jetson_nano": round(size_jetson, 2),
            "desktop_pc": round(size_pc, 2),
            "aws_server": round(size_aws, 2)
        },
        "size_score_latency": int(size_latency),
        "dataset_and_code_score": round(data_set_code_score, 2),
        "dataset_and_code_score_latency": int(data_set_code_latency),
        "dataset_quality": round(data_score, 2),
        "dataset_quality_latency": int(data_latency),
        "code_quality": round(code_score, 2),
        "code_quality_latency": int(code_latency)
        ,"reproducibility": round(reproducibility_score, 2)
        ,"reproducibility_latency" : int(reproducibility_latency)
        ,"reviewedness": round(reviewedness_score, 2)
        ,"reviewedness_latency" : int(reviewedness_latency)
    }

from src.services.auth import verify_api_key
from src.metrics.sandbox_runner import run_metric_in_sandbox

def run_all_metrics_triggered(user_info: dict, model_info):
    # only allow admin role to run full orchestrator
    if "admin" not in user_info.get("roles", []):
        raise PermissionError("Only admin users may trigger full metric runs")
    # For each metric that requires running untrusted code, call sandbox runner
    # Example: call an external script that runs metrics
    cmd = ["python", "src/metrics/run_all_metrics_cli.py", "--model", model_info["s3_key"]]
    returncode, out, err = run_metric_in_sandbox(cmd, timeout=120)
    # parse output etc.
