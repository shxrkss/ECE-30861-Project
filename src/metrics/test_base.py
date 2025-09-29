import pytest
from src.metrics.base import MetricBase

def test_initialization():
    metric = MetricBase("TestMetric")
    assert metric.name == "TestMetric"
    assert metric.value == 0.0

def test_compute_not_implemented():
    metric = MetricBase("TestMetric")
    with pytest.raises(NotImplementedError):
        metric.compute("http://example.com")

def test_is_applicable_default():
    metric = MetricBase("TestMetric")
    # Should return True for any URL
    assert metric.is_applicable("http://example.com")
    assert metric.is_applicable("")
    assert metric.is_applicable(None)
