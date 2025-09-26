# data_code_quality_metric_llm.py
from __future__ import annotations
import os, re, json, requests
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from huggingface_hub import HfApi
from base import MetricBase
from utils.tools import clamp

DEFAULT_BASE_URL = os.getenv("PURDUE_GENAI_BASE_URL", "https://genai.rcac.purdue.edu/api/chat/completions")
DEFAULT_MODEL    = os.getenv("PURDUE_GENAI_MODEL", "llama3.1:latest")
API_KEY          = os.getenv("sk-8b9cb21df127427c8cad5deb382bb706")

# ---------- Prompt (schema-first, strict JSON) ----------
SYSTEM_PROMPT = (
    "You are a strict evaluator. Output valid minified JSON only. No commentary."
)

USER_PROMPT_TEMPLATE = r"""
Read the provided model README (unstructured text) and return ONLY valid minified JSON matching this schema:

{
  "dataset_and_code_score": <0..1>,
  "subscores": {
    "dataset_presence": <0|1>,
    "dataset_detail": <0..1>,
    "dataset_links": <0|1>,
    "code_presence": <0..1>,
    "code_quality": <0..1>
  },
  "evidence": {
    "datasets": [<up to 8 dataset/benchmark names>],
    "links": [<up to 8 relevant URLs>],
    "code_block_count": <int>
  }
}

Scoring rubric (weights form the final score):
- dataset_presence (0.20): 1 if training OR eval datasets are explicitly named (e.g., “C4”, “The Pile”, “GLUE”, “SQuAD”, “MMLU”, etc.).
- dataset_detail (0.25): normalize by clues present (splits, preprocessing, size/samples, licensing/citation, curation rationale). Scale hits/4, cap at 1.
- dataset_links (0.15): 1 if README links to dataset pages or authoritative sources (HF datasets, Kaggle, arXiv, project sites).
- code_presence (0.20): 1.0 if ≥2 fenced code blocks showing usage/train/eval; 0.7 if exactly 1; 0.3 if none but explicit “pip install/requirements/Colab” text; else 0.
- code_quality (0.20): normalize by quality signals (pip/requirements/Trainer/evaluate/Colab/notebook/torchrun/accelerate/seed/reproducibility). Scale hits/5, cap at 1.

Rules: Be conservative. Do NOT infer missing info. If README lacks something, score that part 0. Output JSON only.

README:
<<<BEGIN_README>>>
{README_TEXT}
<<<END_README>>>
""".strip()

# ---------- Utility ----------
def _url_to_repo_id(url: str) -> str:
    p = urlparse(url)
    parts = [s for s in p.path.split("/") if s]
    if not parts:
        raise ValueError(f"Invalid HF URL: {url}")
    # first 1–2 segments only (ignore /tree/main, /blob/.., etc.)
    return parts[0] if len(parts) == 1 else "/".join(parts[:2])

def _safe_minified_json(s: str) -> Dict[str, Any]:
    """
    Parse the model's reply into a JSON object. Strips accidental code-fence
    wrappers and trailing commentary.
    """
    if s is None:
        raise ValueError("Empty LLM response.")
    # strip common Markdown fences
    s2 = s.strip()
    if s2.startswith("```"):
        s2 = re.sub(r"^```(json)?", "", s2.strip(), flags=re.IGNORECASE).strip()
        s2 = re.sub(r"```$", "", s2).strip()
    # find first '{' ... last '}' to be defensive
    start = s2.find("{")
    end   = s2.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in LLM response.")
    s3 = s2[start:end+1]
    return json.loads(s3)

def _post_chat(base_url: str, api_key: str, model: str, system: str, user: str, timeout: int = 90) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "stream": False
    }
    r = requests.post(base_url, headers=headers, json=body, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    # OpenAI-compatible response
    return data["choices"][0]["message"]["content"]

def _get_readme(repo_id: str, hf_token: Optional[str] = None, max_chars: int = 150_000) -> str:
    mc = HfApi().model_card(repo_id, token=hf_token)
    txt = (mc.content or "") if mc else ""
    # Light truncation to respect context limits
    return txt[:max_chars]

def _weighted_score(sub: Dict[str, float]) -> float:
    # same weights as in the rubric inside the prompt
    w = {
        "dataset_presence": 0.20,
        "dataset_detail":   0.25,
        "dataset_links":    0.15,
        "code_presence":    0.20,
        "code_quality":     0.20,
    }
    total = 0.0
    for k, wk in w.items():
        total += wk * float(sub.get(k, 0.0))
    return clamp(total)

# ---------- Metric ----------
class DataAndCodeQualityMetricLLM(MetricBase):
    """
    LLM-based evaluator for dataset & code quality in a model README.
    Returns a float in [0,1]. Use explain() to get subscores & evidence.
    """
    def __init__(self,
                 base_url: Optional[str] = None,
                 model: Optional[str] = None,
                 api_key: Optional[str] = None) -> None:
        super().__init__("dataset_and_code_llm")
        self.base_url = base_url or DEFAULT_BASE_URL
        self.model    = model or DEFAULT_MODEL
        self.api_key  = api_key or API_KEY
        if not self.api_key:
            raise RuntimeError("PURDUE_GENAI_API_KEY not set. Export it or pass api_key=...")

    def compute(self, url: str, hf_token: Optional[str] = None) -> float:
        repo_id = _url_to_repo_id(url)
        readme  = _get_readme(repo_id, hf_token=hf_token)
        user_prompt = USER_PROMPT_TEMPLATE.replace("{README_TEXT}", readme)
        content = _post_chat(self.base_url, self.api_key, self.model, SYSTEM_PROMPT, user_prompt)
        parsed  = _safe_minified_json(content)

        # If the model already returned a final "dataset_and_code_score", respect it.
        if "dataset_and_code_score" in parsed and "subscores" in parsed:
            try:
                return clamp(float(parsed["dataset_and_code_score"]))
            except Exception:
                pass

        # Otherwise compute from subscores (defensive)
        subs = parsed.get("subscores", {})
        return _weighted_score(subs)

    def explain(self, url: str, hf_token: Optional[str] = None) -> Dict[str, Any]:
        repo_id = _url_to_repo_id(url)
        readme  = _get_readme(repo_id, hf_token=hf_token)
        user_prompt = USER_PROMPT_TEMPLATE.replace("{README_TEXT}", readme)
        content = _post_chat(self.base_url, self.api_key, self.model, SYSTEM_PROMPT, user_prompt)
        parsed  = _safe_minified_json(content)
        # Always include a final score field for debugging dashboards
        subs = parsed.get("subscores", {})
        parsed["final_score"] = clamp(
            float(parsed.get("dataset_and_code_score", _weighted_score(subs)))
        )
        return parsed
