import pytest
from unittest.mock import patch
from orchestrator import run_all_metrics

@patch("src.metrics.bus_metric.BusMetric")
@patch("src.metrics.code_quality_metric.CodeQualityMetric")
@patch("src.metrics.dataset_quality_metric.DataQualityMetric")
@patch("src.metrics.license_metric.LicenseMetric")
def test_run_all_metrics(mock_license, mock_data, mock_code, mock_bus):
    # Setup mock return values (score, latency)
    mock_bus.return_value.compute.return_value = (0.8, 10)
    mock_code.return_value.compute.return_value = (0.9, 20)
    mock_data.return_value.compute.return_value = (0.95, 15)
    mock_license.return_value.compute.return_value = (1.0, 5)

    # Sample repo info
    repo_info = (
        "https://github.com/google-research/bert",
        "https://huggingface.co/datasets/bookcorpus/bookcorpus",
        "https://huggingface.co/google-bert/bert-base-uncased"
    )

    # Run the function
    results = run_all_metrics(repo_info)

    # Verify the results
    assert isinstance(results, dict), "Results should be a dictionary"
    assert len(results) > 0, "Results should not be empty"

    # Check that all metrics return a number
    for metric_name, score in results.items():
        if isinstance(score, dict):
            # Some metrics like size_score return a dict of device scores
            for device_score in score.values():
                assert isinstance(device_score, (int, float))
        else:
            assert isinstance(score, (int, float)), f"Score for {metric_name} should be a number"

    print("Test passed! Results:")
    print(results)
