# performance_claim_metric_llm.py
from __future__ import annotations
import os, re, json, time, requests
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse
from dotenv import load_dotenv, find_dotenv

from huggingface_hub import HfApi, ModelCard, hf_hub_download
from base import MetricBase
from utils.tools import clamp
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

# ======= Config (only API key is required via env) =======
GENAI_BASE_URL  = "https://genai.rcac.purdue.edu/api/chat/completions"
GENAI_MODEL     = "llama3.1:latest"
API_KEY_ENV     = "GEN_AI_STUDIO_API_KEY"   
TIMEOUT_SEC     = int(os.getenv("GENAI_TIMEOUT_SEC", "90"))
README_MAX_CHARS= int(os.getenv("README_MAX_CHARS", "30000"))

SYSTEM_PROMPT = "You are a strict evaluator. Output valid minified JSON only. No commentary."

USER_PROMPT = r"""
You are given unstructured README text and selected Hub metadata.
Extract performance claims (benchmarks + metrics + numeric values), assess the strength of evidence, and return ONLY valid minified JSON:

{
  "performance_claim_score": <0..1>,
  "subscores": {
    "presence": <0..1>,
    "detail": <0..1>,
    "evidence": <0..1>,
    "confirmation": <0..1>
  },
  "evidence_tier": "<none|weak|readme_numeric|repro|confirmed>",
  "evidence_items": [
    {"type":"section|setup|script|seed|hardware|dataset_link|paper|leaderboard|pwc|repo",
     "value":"<short text or URL>",
     "authority":"low|medium|high"}
  ],
  "claims": [
    {"benchmark":"", "metric":"", "value": <float>, "unit":"%|score|other", "split":"", "task":"", "link":""}
  ]
}

Scoring rubric (compute subscores in [0..1] and a FINAL score using these weights EXACTLY):
- presence  (45%): 1 if any numeric benchmark claims (README or model-index); else 0.
- detail    (15%): scale by clarity/coverage of dataset/task/split/metric/value (0=none, 1=all present).
- evidence  (10%): strength of supporting material
- confirmation (30%): 1.0 for authoritative external links or well-formed model-index corroboration; 0.5 for some links of unclear authority; 0.0 otherwise.

Rules:
- Be conservative; do NOT infer missing info.
- Prefer authoritative sources (leaderboards, papers, PWC) over blogs/tweets.
- When multiple claims exist, score based on the overall strength of evidence across them.
- Output minified JSON ONLY. No commentary, no code fences.

README_AND_METADATA:
<<<
{TEXT}
>>>
""".strip()

# ======= Helpers =======
def _url_to_repo(url: str) -> Tuple[str, str]:
    """Return (repo_id, repo_type) where repo_type in {'model','space','dataset'}."""
    p = urlparse(url)
    parts = [s for s in p.path.split("/") if s]
    if not parts:
        raise ValueError(f"Invalid HF URL: {url}")
    head = parts[0].lower()
    if head in ("spaces", "space"):   return "/".join(parts[1:3]), "space"
    if head in ("datasets", "dataset"): return "/".join(parts[1:3]), "dataset"
    return (parts[0] if len(parts) == 1 else "/".join(parts[:2])), "model"

def _safe_json(s: str) -> Dict[str, Any]:
    if not s: raise ValueError("Empty LLM response.")
    t = s.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(json)?", "", t, flags=re.I).strip()
        t = re.sub(r"```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i == -1 or j == -1 or j < i:
        raise ValueError("No JSON object found.")
    return json.loads(t[i:j+1])

def _post_chat(base_url: str, api_key: str, model: str, system: str, user: str,
               timeout: int = TIMEOUT_SEC, retries: int = 3, backoff: float = 0.8) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": model,
        "messages": [{"role":"system","content":system},{"role":"user","content":user}],
        "temperature": 0, "stream": False, "max_tokens": 800
    }
    last = None
    for k in range(retries):
        try:
            r = requests.post(base_url, headers=headers, json=body, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            last = e
            time.sleep(backoff * (2**k))
    raise RuntimeError(f"GenAI request failed: {last}")

def _get_readme(repo_id: str, repo_type: str, hf_token: Optional[str]) -> str:
    # 1) ModelCard.load
    try:
        mc = ModelCard.load(repo_id, token=hf_token, repo_type=repo_type)
        if mc and mc.content:
            return mc.content[:README_MAX_CHARS]
    except Exception:
        pass
    # 2) Direct README files
    for fname in ("README.md","README.rst","README.txt"):
        try:
            p = hf_hub_download(repo_id=repo_id, repo_type=repo_type, token=hf_token, filename=fname)
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
            if txt: return txt[:README_MAX_CHARS]
        except Exception:
            continue
    return ""

def _metadata_block(repo_id: str, repo_type: str, hf_token: Optional[str]) -> str:
    """Serialize useful Hub metadata for the LLM to see (models only)."""
    if repo_type != "model": return ""
    try:
        info = HfApi().model_info(repo_id, token=hf_token, expand=["cardData","model-index","tags","widgetData"])
    except Exception:
        return ""
    parts = []
    if getattr(info, "cardData", None):
        try: parts.append("CARD_DATA:\n" + json.dumps(info.cardData)[:8000])
        except Exception: pass
    try:
        d = info.dict()
        mi = d.get("model-index") or d.get("modelIndex") or d.get("model_index")
        if mi: parts.append("MODEL_INDEX:\n" + json.dumps(mi)[:8000])
    except Exception: pass
    if getattr(info, "tags", None):
        parts.append("TAGS:\n" + json.dumps(info.tags)[:3000])
    if getattr(info, "widgetData", None):
        parts.append("WIDGET_DATA:\n" + json.dumps(info.widgetData)[:3000])
    return ("\n\n".join(parts))[:12000]

def _weighted_score(sub: Dict[str, float]) -> float:
    # equal weights (0.25 each)
    w = {"presence":0.25,"detail":0.25,"evidence":0.25,"confirmation":0.25}
    return clamp(sum(w[k]*float(sub.get(k,0.0)) for k in w))

# ======= Metric =======
class PerformanceClaimMetricLLM(MetricBase):
    """
    LLM-based performance claim evaluator.
    Returns a float in [0,1]. Uses only GEN_AI_STUDIO_API_KEY from env.
    """
    def __init__(self, debug: bool = False) -> None:
        super().__init__("performance_claim_llm")
        self.api_key = os.getenv("GEN_AI_STUDIO_API_KEY")
        if not self.api_key:
            raise RuntimeError(f"Missing {API_KEY_ENV}. Set it in your environment.")
        self.debug = debug
        self.last_raw_reply_head = ""

    def compute(self, url: str, hf_token: Optional[str] = None) -> float:
        repo_id, repo_type = _url_to_repo(url)
        readme = _get_readme(repo_id, repo_type, hf_token)
        meta   = _metadata_block(repo_id, repo_type, hf_token)
        text   = (readme or "") + ("\n\n### HUB_METADATA ###\n" + meta if meta else "")

        user = USER_PROMPT.replace("{TEXT}", text)
        content = _post_chat(GENAI_BASE_URL, self.api_key, GENAI_MODEL, SYSTEM_PROMPT, user)
        if self.debug:
            self.last_raw_reply_head = (content or "")[:800]

        # Try to parse. If we got prose, convert with a tiny follow-up call.
        try:
            parsed = _safe_json(content)
        except Exception:
            # Convert prose -> JSON
            convert_prompt = (
                'Convert the text below into ONLY minified JSON with keys '
                '{"performance_claim_score":<0..1>,"subscores":{"presence":<0..1>,"detail":<0..1>,"evidence":<0..1>,"confirmation":<0..1>},"claims":[]} . '
                'If info missing, use zeros/empty. No commentary.\nTEXT:\n<<<\n' + (content or "") + '\n>>>'
            )
            content2 = _post_chat(GENAI_BASE_URL, self.api_key, GENAI_MODEL, SYSTEM_PROMPT, convert_prompt)
            parsed = _safe_json(content2)

        # Prefer model's top-level score; else compute from subscores
        subs = parsed.get("subscores", {})
        if "performance_claim_score" in parsed:
            try:
                return clamp(float(parsed["performance_claim_score"]))
            except Exception:
                pass
        return _weighted_score(subs)

    # Optional helper for debugging
    def explain(self, url: str, hf_token: Optional[str] = None) -> Dict[str, Any]:
        score = self.compute(url, hf_token=hf_token)
        return {
            "score": round(score,3),
            "raw_reply_head": self.last_raw_reply_head
        }

# ---- Quick CLI test ----
if __name__ == "__main__":
    metric = PerformanceClaimMetricLLM(debug=True)
    tests = [
        "https://huggingface.co/google-bert/bert-base-uncased",
        "https://huggingface.co/parvk11/audience_classifier_model",
        "https://huggingface.co/openai/whisper-tiny",
    ]
    for u in tests:
        try:
            s = metric.compute(u, hf_token=os.getenv("HF_TOKEN"))
            print(f"{u} -> {s:.3f}")
        except Exception as e:
            print("Error:", u, e)
