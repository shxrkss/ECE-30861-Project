import math
import pytest
from unittest.mock import patch, MagicMock
from metrics.bus_metric import BusMetric  

def test_compute_returns_zero_for_none_url():
    metric = BusMetric()
    score, latency = metric.compute(None)
    assert score == 0.0
    assert latency == 0


@patch("src.metrics.bus_metric.HfApi")
def test_get_hf_contributor_stats_parses_commits(mock_hfapi):
    # Arrange
    metric = BusMetric()

    # Mock commit objects
    mock_commit1 = MagicMock()
    mock_commit1.authors = ["alice"]

    mock_commit2 = MagicMock()
    mock_commit2.authors = ["alice", "bob"]

    mock_hfapi.return_value.list_repo_commits.return_value = [mock_commit1, mock_commit2]

    # Act
    N, C, ci = metric.get_hf_contributor_stats("https://huggingface.co/org/repo")

    # Assert
    assert N == 2   # 2 unique contributors
    assert C == 3   # total contributions (alice twice, bob once)
    assert ci == {"alice": 2, "bob": 1}


@patch("src.metrics.bus_metric.HfApi")
def test_compute_entropy_based_score(mock_hfapi):
    metric = BusMetric()

    # Fake commits: 2 contributors with equal contributions
    mock_commit1 = MagicMock()
    mock_commit1.authors = ["alice"]

    mock_commit2 = MagicMock()
    mock_commit2.authors = ["bob"]

    mock_hfapi.return_value.list_repo_commits.return_value = [mock_commit1, mock_commit2]

    score, latency = metric.compute("https://huggingface.co/org/repo")

    # For equal contributions, entropy = max_entropy, so score ~ 1.0
    assert pytest.approx(score, rel=1e-3) == 1.0
    assert latency >= 0


@patch("src.metrics.bus_metric.HfApi")
def test_compute_returns_zero_for_single_contributor(mock_hfapi):
    metric = BusMetric()

    # One contributor only
    mock_commit = MagicMock()
    mock_commit.authors = ["alice"]

    mock_hfapi.return_value.list_repo_commits.return_value = [mock_commit]

    score, latency = metric.compute("https://huggingface.co/org/repo")

    assert score == 0.0
    assert latency >= 0


@patch("src.metrics.bus_metric.HfApi")
def test_get_hf_contributor_stats_handles_error(mock_hfapi):
    metric = BusMetric()

    # Simulate API failure
    mock_hfapi.return_value.list_repo_commits.side_effect = Exception("API down")

    N, C, ci = metric.get_hf_contributor_stats("https://huggingface.co/org/repo")

    assert N == 0
    assert C == 0
    assert ci == {}
