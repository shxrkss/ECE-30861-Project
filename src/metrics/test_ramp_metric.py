import pytest
from unittest.mock import patch, MagicMock
from src.metrics.ramp_metric import RampMetric
from src.metrics.utils.tools import clamp


def test_clamp_usage():
    """Test that ramp score is clamped between 0 and 1."""
    metric = RampMetric()
    # Clamp should never exceed 1
    assert clamp(1.5) == 1.0
    # Clamp should never go below 0
    assert clamp(-0.5) == 0.0
    # Clamp should pass values within range
    assert clamp(0.7) == 0.7


@patch("src.metrics.ramp_metric.requests.get")
@patch("src.metrics.ramp_metric.time.time", side_effect=[0, 0.1])
@patch("src.metrics.ramp_metric.extract_model_or_dataset_id", return_value="dummy-model")
def test_get_downloads_and_latency(mock_id, mock_time, mock_get):
    """Test that get_downloads_and_latency returns downloads and latency correctly."""
    metric = RampMetric()
    # Mock API response
    mock_response = MagicMock()
    mock_response.json.return_value = {"downloads": 1000}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    downloads, latency = metric.get_downloads_and_latency("https://huggingface.co/openai/dummy-model")
    assert downloads == 1000
    # latency in milliseconds, mocked time difference = 0.1s -> 100ms
    assert abs(latency - 100) < 1e-6


@patch("src.metrics.ramp_metric.RampMetric.get_downloads_and_latency")
def test_compute_valid(mock_get_dl):
    """Test compute returns correct ramp score and latency for valid downloads."""
    metric = RampMetric()
    mock_get_dl.return_value = (1000, 50.0)

    ramp_score, latency = metric.compute("https://huggingface.co/openai/dummy-model")
    # ramp_score calculation: (log(1000)-5)/10
    import math
    expected_score = clamp((math.log(1000) - 5) / 10)
    assert ramp_score == expected_score
    assert latency == 50.0


@patch("src.metrics.ramp_metric.RampMetric.get_downloads_and_latency")
def test_compute_invalid(mock_get_dl):
    """Test compute returns None when downloads are invalid."""
    metric = RampMetric()
    # None downloads
    mock_get_dl.return_value = (None, None)
    result = metric.compute("https://huggingface.co/openai/dummy-model")
    assert result == (0.0, 0)

    # Zero downloads
    mock_get_dl.return_value = (0, 10.0)
    result = metric.compute("https://huggingface.co/openai/dummy-model")
    assert result == (0.0, 0)

    # Negative downloads
    mock_get_dl.return_value = (-10, 10.0)
    result = metric.compute("https://huggingface.co/openai/dummy-model")
    assert result == (0.0, 0)
