import pytest
from src.metrics.reviewedness_metric import ReviewednessMetric

@pytest.fixture
def metric():
    return ReviewednessMetric()

def test_extract_github_repo_success(monkeypatch, metric):
    """Should find GitHub repo link in model card."""
    def mock_model_info(model_id):
        class MockInfo:
            cardData = {"text": "Code here: https://github.com/acme/test-repo"}
        return MockInfo()
    monkeypatch.setattr(metric.hf, "model_info", mock_model_info)
    repo = metric.extract_github_repo("https://huggingface.co/acme/model")
    assert repo == "acme/test-repo"

def test_extract_github_repo_missing(monkeypatch, metric):
    """Should return empty string when no GitHub link found."""
    def mock_model_info(model_id):
        class MockInfo:
            cardData = {"text": "no github link here"}
        return MockInfo()
    monkeypatch.setattr(metric.hf, "model_info", mock_model_info)
    assert metric.extract_github_repo("fakeurl") == ""

def test_get_reviewed_fraction_all_reviewed(monkeypatch, metric):
    """Should return 1.0 when all PRs have reviews."""
    def mock_get(url, headers, timeout):
        class MockResponse:
            def json(self_inner):
                if "pulls" in url:
                    return [
                        {"merged_at": "yes", "additions": 10, "deletions": 2, "review_comments_url": "url1"},
                        {"merged_at": "yes", "additions": 5, "deletions": 1, "review_comments_url": "url2"},
                    ]
                else:
                    return [{"id": 1}, {"id": 2}]
        return MockResponse()
    monkeypatch.setattr("requests.get", mock_get)
    assert metric.get_reviewed_fraction("acme/test-repo") == 1.0

def test_get_reviewed_fraction_partial(monkeypatch, metric):
    """Should return 0.5 when half of the lines are reviewed."""
    def mock_get(url, headers, timeout):
        class MockResponse:
            def json(self_inner):
                if "pulls" in url:
                    return [
                        {"merged_at": "yes", "additions": 10, "deletions": 0, "review_comments_url": "url1"},
                        {"merged_at": "yes", "additions": 10, "deletions": 0, "review_comments_url": "url2"},
                    ]
                elif "url1" in url:
                    return [{"id": 1}]  # reviewed
                else:
                    return []  # no reviews
        return MockResponse()
    monkeypatch.setattr("requests.get", mock_get)
    assert metric.get_reviewed_fraction("acme/test-repo") == 0.5

def test_compute_no_repo(monkeypatch, metric):
    """Should return -1 if no GitHub repo found."""
    monkeypatch.setattr(metric, "extract_github_repo", lambda url: "")
    score, latency = metric.compute("https://huggingface.co/none")
    assert score == -1.0
    assert latency >= 0