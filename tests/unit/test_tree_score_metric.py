import os
import json
import pytest
from src.metrics.tree_score_metric import TreeScoreMetric

@pytest.fixture
def temp_registry(tmp_path):
    root = tmp_path / "registry"
    os.makedirs(root)
    # create base model
    base = root / "base-model"
    os.makedirs(base)
    with open(base / "config.json", "w") as f:
        json.dump({"base_model_name_or_path": None}, f)

    # derived model
    derived = root / "derived-model"
    os.makedirs(derived)
    with open(derived / "config.json", "w") as f:
        json.dump({"base_model_name_or_path": "base-model"}, f)
    return root

def test_tree_score_complete(temp_registry):
    metric = TreeScoreMetric()
    score, latency = metric.compute("derived-model", temp_registry)
    assert score == 1.0
    assert latency >= 0

def test_tree_score_missing_config(temp_registry):
    metric = TreeScoreMetric()
    missing_dir = temp_registry / "missing-model"
    os.makedirs(missing_dir)
    score, latency = metric.compute("missing-model", temp_registry)
    assert score == 0.0