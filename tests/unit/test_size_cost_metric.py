import pytest
from src.metrics.size_cost_metric import SizeCostMetric

def test_size_cost_hf(monkeypatch):
    metric = SizeCostMetric()

    # mock HF call
    monkeypatch.setattr(metric, "_get_hf_size", lambda _: 500.0)
    score, latency = metric.compute("https://huggingface.co/test/model")
    assert 0 < score <= 1
    assert latency >= 0

def test_size_cost_s3(monkeypatch):
    metric = SizeCostMetric()
    monkeypatch.setattr(metric, "_get_s3_size", lambda b, p: 250.0)
    score, latency = metric.compute("s3://bucket-name/model.zip")
    assert 0 < score <= 1