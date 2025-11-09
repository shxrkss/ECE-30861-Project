from urllib.parse import urlparse

def is_hf_model(u: str):
    return "huggingface.co" in u and "/datasets/" not in u

def is_hf_dataset(u: str):
    return "huggingface.co" in u and "/datasets/" in u

def is_github(u: str):
    return "github.com" in u

def test_hf_model_dataset_github():
    assert is_hf_model("https://huggingface.co/google/gemma-2b")
    assert is_hf_dataset("https://huggingface.co/datasets/allenai/c4")
    assert is_github("https://github.com/pallets/click")
