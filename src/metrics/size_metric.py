# size_metric.py  (REPLACEMENT)
from __future__ import annotations
import math, re
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import os

from huggingface_hub import HfApi
from transformers import AutoConfig, AutoModel
from accelerate import init_empty_weights  # avoids allocating weights
from metrics.base import MetricBase
from metrics.utils.tools import clamp

# -------------------
# Helpers / constants
# -------------------
PARAM_KEYS = ["model_parameters", "num_parameters", "parameters", "parameter_count", "params", "model_size"]

# Memory per parameter by precision (bytes)
PRECISION_BYTES = {
    "fp32": 4.0,
    "fp16": 2.0,
    "int8": 1.0,
    "4bit": 0.5,
}

# Default device profiles (you can override via compute(..., profiles=...))
DEFAULT_PROFILES: Dict[str, Dict[str, Any]] = {
    # Raspberry Pi 4/5 8GB (CPU int8/4bit; leave headroom for OS/runtime)
    "raspberry_pi": {"mem_bytes": 6.0e9, "supports_gpu": False, "comfort_params": 5e7},   # ~50M comfy
    # Jetson Nano 4GB VRAM (FP16 possible; small headroom)
    "jetson_nano":  {"mem_bytes": 3.0e9, "supports_gpu": True,  "comfort_params": 1e8},   # ~100M comfy
    # Desktop PC with ~12GB GPU VRAM
    "desktop_pc":   {"mem_bytes": 12.0e9, "supports_gpu": True, "comfort_params": 2e9},   # ~2B comfy
    # AWS server w/ ~16GB GPU VRAM (adjust per instance)
    "aws_server":   {"mem_bytes": 16.0e9, "supports_gpu": True, "comfort_params": 3e9},   # ~3B comfy
}

def _url_to_repo_id(url: str) -> str:
    p = urlparse(url)
    parts = [s for s in p.path.split("/") if s]
    if not parts:
        raise ValueError(f"Invalid HF URL: {url}")
    # repo id is first 1–2 segments; ignore UI suffixes like /tree/main
    return parts[0] if len(parts) == 1 else "/".join(parts[:2])

def _parse_param_str(v) -> Optional[float]:
    if isinstance(v, (int, float)):
        return float(v)
    if not isinstance(v, str):
        return None
    s = v.strip().upper().replace(",", "")
    # numeric string
    try:
        return float(s)
    except ValueError:
        pass
    # 7B / 258M / 3.5K
    m = re.fullmatch(r"([0-9]*\.?[0-9]+)\s*([KMB])", s)
    if m:
        num, unit = float(m.group(1)), m.group(2)
        return num * (1e3 if unit == "K" else 1e6 if unit == "M" else 1e9)
    # 7 BILLION / 110 MILLION
    m2 = re.fullmatch(r"([0-9]*\.?[0-9]+)\s*(THOUSAND|MILLION|BILLION)", s)
    if m2:
        num, unit = float(m2.group(1)), m2.group(2)
        return num * (1e3 if unit == "THOUSAND" else 1e6 if unit == "MILLION" else 1e9)
    return None

def _get_params_from_card(repo_id: str, token: Optional[str] = None) -> Optional[float]:
    info = HfApi().model_info(repo_id, token=token, expand=["cardData"])
    card = info.cardData or {}
    for k in PARAM_KEYS:
        if k in card:
            parsed = _parse_param_str(card[k])
            if parsed and parsed > 0:
                return parsed
    # optional: light README scan for "Model size ... params"
    if info.cardData is None:
        try:
            mc = HfApi().model_card(repo_id, token=token)
            txt = (mc.content or "")
            m = re.search(r"Model\s*size\s*[:\-]?\s*([0-9][0-9.,]*\s*[KMB]|[0-9][0-9.,]*)\s*params?", txt, re.I)
            if m:
                parsed = _parse_param_str(m.group(1))
                if parsed and parsed > 0:
                    return parsed
        except Exception:
            pass
    return None

def _get_params_from_config(repo_id: str, token: Optional[str] = None) -> int:
    """
    Build on a meta device (no weight download) and count params.
    Works for models supported by `transformers`.
    """
    cfg = AutoConfig.from_pretrained(repo_id, token=token)
    with init_empty_weights():
        model = AutoModel.from_config(cfg)
    return int(sum(p.numel() for p in model.parameters()))

def _memory_with_overhead(params: float, precision: str, overhead: float) -> float:
    return params * PRECISION_BYTES[precision] * overhead

def _pick_best_precision(params: float, mem_cap: float, supports_gpu: bool, overhead: float) -> Optional[str]:
    # Prefer higher-precision if GPU available; CPU prefers quantized
    order = ["fp16", "int8", "4bit"] if supports_gpu else ["int8", "4bit", "fp32"]
    for prec in order:
        need = _memory_with_overhead(params, prec, overhead)
        if need <= mem_cap:
            return prec
    return None

def _base_score_for_precision(prec: Optional[str]) -> float:
    if prec is None: return 0.0
    if prec == "fp16": return 1.0
    if prec == "int8": return 0.85
    if prec == "4bit": return 0.70
    if prec == "fp32": return 0.60
    return 0.0

def _throughput_penalty(params: float, comfort_params: float, softness: float = 1.2) -> float:
    """
    ~1.0 when params << comfort, decays as params grows beyond comfort.
    penalty = 1 / (1 + (params / comfort)^softness)
    """
    r = (params / max(1.0, comfort_params)) ** softness
    return 1.0 / (1.0 + r)

class SizeMetric(MetricBase):
    """
    Computes device-compatibility scores (0–1) for a model, keyed by device:
      {'raspberry_pi': x, 'jetson_nano': y, 'desktop_pc': z, 'aws_server': w}
    """
    def __init__(self, overhead_factor: float = 1.3) -> None:
        super().__init__("size_compat")
        self.overhead = overhead_factor  # slack for KV cache/activations/runtime

    def _get_params(self, repo_id: str, hf_token: Optional[str]) -> float:
        params = _get_params_from_card(repo_id, token=hf_token)
        if not params:
            params = _get_params_from_config(repo_id, token=hf_token)
        if params <= 0:
            raise ValueError("Parameter count must be positive")
        return float(params)

    def compute(self, url: str, hf_token: Optional[str] = None,
                profiles: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, float]:
        """
        Returns dict of device -> score in [0,1].
        Optionally override device profiles via `profiles`.
        """
        repo_id = _url_to_repo_id(url)
        params = self._get_params(repo_id, hf_token=hf_token)
        profs = profiles or DEFAULT_PROFILES

        results: Dict[str, float] = {}
        for device, cfg in profs.items():
            mem_cap = float(cfg["mem_bytes"])
            supports_gpu = bool(cfg["supports_gpu"])
            comfort = float(cfg["comfort_params"])

            best_prec = _pick_best_precision(params, mem_cap, supports_gpu, self.overhead)
            base = _base_score_for_precision(best_prec)
            penalty = _throughput_penalty(params, comfort)
            results[device] = clamp(base * penalty)

        return results

if __name__ == "__main__":
    # "Overhead factor" is a simple multiplier that inflates pure weight memory (params × bytes/param) 
    # to account for all the extra runtime memory a model actually needs at inference time.
    # For our case, we can use 1.3
    metric = SizeMetric(overhead_factor=1.3)
    urls = [
        "https://huggingface.co/google-bert/bert-base-uncased",  # ~110M
        "https://huggingface.co/openai/whisper-tiny",            # ~39M
    ]
    for u in urls:
        try:
            scores = metric.compute(u, hf_token=os.getenv("HF_TOKEN"))
            print(u)
            for k, v in scores.items():
                print(f"  {k:13s} -> {v:.2f}")
        except Exception as e:
            print("Error:", u, e)

