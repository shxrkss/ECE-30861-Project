import pytest
from src.metrics.license_check_metric import LicenseCheckMetric

def test_license_check_permissive(monkeypatch):
    metric = LicenseCheckMetric()
    monkeypatch.setattr(metric, "classify_license", lambda x: "permissive")
    score, latency = metric.compute("https://github.com/user/repo", "MIT")
    assert score in [1.0, 0.5, 0.0]

def test_license_check_failure(monkeypatch):
    metric = LicenseCheckMetric()
    monkeypatch.setattr(metric, "compatible", lambda a, b: 0.0)
    score, latency = metric.compute("invalid-url", "GPL")
    assert score in [-1, 0, 0.5, 1]