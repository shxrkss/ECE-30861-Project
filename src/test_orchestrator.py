import pytest
from src.orchestrator import run_all_metrics

def test_run_all_metrics():
    # Sample data
    repo_info = (
        "https://github.com/google-research/bert",  # code_url
        "https://huggingface.co/datasets/bookcorpus/bookcorpus",  # dataset_url
        "https://huggingface.co/google-bert/bert-base-uncased"  # model_url
    )

    # Run the function
    results = run_all_metrics(repo_info)

    # Verify the results
    assert isinstance(results, dict), "Results should be a dictionary"
    assert len(results) > 0, "Results should not be empty"

    # Check that all metrics return a score
    for metric_name, score in results.items():
        assert isinstance(metric_name, str), f"Metric name {metric_name} should be a string"
        assert isinstance(score, (int, float)), f"Score for {metric_name} should be a number"
        assert score >= -1.0, f"Score for {metric_name} should be -1.0 or higher"

    print("Test passed! Results:")
    print(results)