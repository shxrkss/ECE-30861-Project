# src/metrics/test_size_metric.py
import pytest
import sys
from unittest.mock import MagicMock, patch

# -----------------------
# Mock heavy dependencies
# -----------------------
sys.modules['transformers'] = MagicMock()
sys.modules['transformers'].AutoConfig = MagicMock()
sys.modules['transformers'].AutoModel = MagicMock()
sys.modules['accelerate'] = MagicMock()
sys.modules['accelerate'].init_empty_weights = MagicMock()
sys.modules['huggingface_hub'] = MagicMock()
sys.modules['huggingface_hub'].HfApi = MagicMock()

# Now import the code under test
from src.metrics.size_metric import SizeMetric, _url_to_repo_id, _parse_param_str, clamp

# -----------------------
# Test helper functions
# -----------------------
def test_url_to_repo_id():
    assert _url_to_repo_id("https://huggingface.co/user/model") == "user/model"
    assert _url_to_repo_id("https://huggingface.co/model") == "model"
    assert _url_to_repo_id("https://huggingface.co/user/model/tree/main") == "user/model"
    with pytest.raises(ValueError):
        _url_to_repo_id("https://huggingface.co/")

def test_parse_param_str():
    assert _parse_param_str("7B") == 7e9
    assert _parse_param_str("258M") == 258e6
    assert _parse_param_str("3.5K") == 3500
    assert _parse_param_str("7 billion") == 7e9
    assert _parse_param_str(123) == 123.0
    assert _parse_param_str(123.4) == 123.4
    assert _parse_param_str(None) is None
    assert _parse_param_str("not_a_number") is None

def test_clamp():
    assert clamp(1.5) == 1.0
    assert clamp(-0.1) == 0.0
    assert clamp(0.5) == 0.5

# -----------------------
# Test SizeMetric.compute
# -----------------------
@pytest.fixture
def mocked_hf_api():
    # Patch HfApi().model_info and model_card
    mock_api = MagicMock()
    mock_api.model_info.return_value.cardData = {"model_parameters": "100M"}
    sys.modules['huggingface_hub'].HfApi.return_value = mock_api
    return mock_api

@pytest.fixture
def mocked_transformers():
    # Patch AutoConfig and AutoModel for fallback
    mock_model = MagicMock()
    mock_model.parameters.return_value = [MagicMock(numel=lambda: 100_000_000)]
    sys.modules['transformers'].AutoModel.from_config.return_value = mock_model
    sys.modules['transformers'].AutoConfig.from_pretrained.return_value = MagicMock()
    return mock_model

