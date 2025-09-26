# performance_claim_metric.py
from __future__ import annotations
import re
import os
from typing import Optional, List, Tuple, Dict, Any
from urllib.parse import urlparse

from huggingface_hub import HfApi
from base import MetricBase
from utils.tools import clamp

# --- Heuristics ---
BENCHMARK_KEYWORDS = [
    # General/LLM
    "mmlu", "hellaswag", "winogrande", "arc", "truthfulqa", "gsm8k",
    "lambada", "piqa", "qnli", "qqp", "mnli", "sst-2", "cola", "rte", "mrpc",  # GLUE
    # QA / Summ / MT / ASR
    "squad", "squad v1", "squad v2", "xquad",
    "rouge", "bleu", "meteor", "chrf",
    "wer", "cer", "ter",
    # Vision
    "imagenet", "cifar-10", "cifar100", "ms coco", "pascal voc", "mnist",
]

METRIC_KEYWORDS = [
    "accuracy", "acc", "f1", "f1-score", "precision", "recall",
    "exact match", "em", "bleu", "rouge", "rouge-l", "meteor", "chrf",
    "perplexity", "ppl", "wer", "cer", "ter",
]

# numeric like "87.5", "87", "87%", "0.875"
NUMERIC_PATTERN = r"(?:\d{1,3}(?:\.\d+)?%?|\.\d+)"

# “authoritative” link domains that suggest stronger confirmation
CONFIRMING_DOMAINS = [
    "paperswithcode.com", "arxiv.org", "open-llm-leaderboard", "mlcommons.org",
    "nlp.stanford.edu", "rajpurkar.github.io", "allenai.org", "mosaicml.com",
]

EVIDENCE_SECTION_HINTS = [
    "evaluation", "results", "benchmarks", "leaderboard", "reproduc",
    "experimental setup", "setup", "methodology",
]

class PerformanceClaimMetric(MetricBase):
    def __init__(self,
                 w_presence: float = 0.25,
                 w_detail: float = 0.25,
                 w_evidence: float = 0.25,
                 w_confirmation: float = 0.25) -> None:
        super().__init__("performance_claim")
        self.w_presence = w_presence
        self.w_detail = w_detail
        self.w_evidence = w_evidence
        self.w_confirmation = w_confirmation

    # -------------------
    # URL -> repo_id
    # -------------------
    def url_to_repo_id(self, url: str) -> str:
        p = urlparse(url)
        parts = [s for s in p.path.split("/") if s]
        if not parts:
            raise ValueError(f"Invalid HF URL: {url}")
        # repo id is first 1–2 segments; ignore UI suffixes (/tree/main, /blob/...)
        return parts[0] if len(parts) == 1 else "/".join(parts[:2])

    def get_model_info(self, repo_id: str, token: Optional[str] = None):
        return HfApi().model_info(
            repo_id,
            token=token,
            expand=["model-index", "cardData"]
        )

    def _get_readme_text(self, repo_id: str, token: Optional[str] = None) -> str:
        # model_info(...).card may be missing; fetch the model card explicitly
        try:
            mc = HfApi().model_card(repo_id, token=token)
            return (mc.content or "") if mc else ""
        except Exception:
            return ""

    def extract_readme_claims(self, readme_text: str):
        """Parse README text for benchmark + metric + numeric-value patterns."""
        if not readme_text:
            return []

        text = readme_text.lower()
        claims = []

        bench_regex = r"|".join([re.escape(k) for k in BENCHMARK_KEYWORDS])
        metric_regex = r"|".join([re.escape(k) for k in METRIC_KEYWORDS])

        # Example: "MMLU accuracy: 72.3%" or "SQuAD EM 88.4"
        pattern = re.compile(
            rf"(?P<bench>{bench_regex}).{{0,40}}(?P<metric>{metric_regex}).{{0,10}}(?P<val>{NUMERIC_PATTERN})",
            re.I | re.M,
        )
        for m in pattern.finditer(text):
            bench = m.group("bench")
            metric = m.group("metric")
            val = self._to_float(m.group("val"))
            if val is not None:
                claims.append((bench, metric, val, {}))

        # Table rows like: "| mmlu | accuracy | 72.3 |"
        table_pat = re.compile(
            rf"\|\s*(?P<bench>{bench_regex})\s*\|\s*(?P<metric>{metric_regex})\s*\|\s*(?P<val>{NUMERIC_PATTERN})\s*\|",
            re.I,
        )
        for m in table_pat.finditer(text):
            bench = m.group("bench")
            metric = m.group("metric")
            val = self._to_float(m.group("val"))
            if val is not None:
                claims.append((bench, metric, val, {"tabular": True}))

        return claims

    def evidence_signals(self, readme_text: str):
        """Lightweight evidence/confirmation heuristics from README text."""
        t = (readme_text or "").lower()

        has_evidence_section = any(h in t for h in EVIDENCE_SECTION_HINTS)
        has_setup = any(k in t for k in [
            "seed","random seed","gpu","hardware","a100","v100","cpu",
            "epochs","batch size","learning rate","eval",
        ])
        has_confirming_links = any(dom in t for dom in CONFIRMING_DOMAINS)

        return {
            "has_evidence_section": has_evidence_section,
            "has_setup": has_setup,
            "has_confirming_links": has_confirming_links,
            "confirming_domains_present": has_confirming_links,
        }

    def extract_model_index_claims(self, info) -> List[Tuple[str, str, float, Dict[str, Any]]]:
        claims = []
        # Handle both camelCase and snake_case (some hub versions/serializations differ)
        idx = getattr(info, "modelIndex", None) or getattr(info, "model_index", None)
        # If info is a pydantic-ish object, .dict() may expose 'model-index'
        if not idx and hasattr(info, "dict"):
            d = info.dict()
            idx = d.get("model-index") or d.get("modelIndex") or d.get("model_index")

        if not isinstance(idx, list):
            return claims

        for entry in idx:
            results = entry.get("results") if isinstance(entry, dict) else None
            if not results:
                continue
            for res in results:
                dataset = ""
                task = ""
                split = ""
                if isinstance(res, dict):
                    ds = res.get("dataset") or {}
                    if isinstance(ds, dict):
                        dataset = ds.get("name") or ""
                        split = ds.get("type") or ds.get("split") or ""
                    t = res.get("task") or {}
                    if isinstance(t, dict):
                        task = t.get("type") or t.get("name") or ""
                    for m in (res.get("metrics") or []):
                        if not isinstance(m, dict): 
                            continue
                        name = (m.get("name") or m.get("type") or "").strip()
                        val = m.get("value")
                        try:
                            fval = float(val)
                        except (TypeError, ValueError):
                            continue
                        if name:
                            claims.append((dataset or task or "", name.lower(), fval, {"split": split, "task": task}))
        return claims

    def compute(self, url: str, hf_token: Optional[str] = None) -> float:
        repo_id = self.url_to_repo_id(url)
        info = self.get_model_info(repo_id, token=hf_token)

        # Structured claims
        structured_claims = self.extract_model_index_claims(info)

        # README text (explicit fetch)
        readme_text = self._get_readme_text(repo_id, token=hf_token)

        # Unstructured claims
        unstructured_claims = self.extract_readme_claims(readme_text)

        # Evidence signals
        signals = self.evidence_signals(readme_text)

        presence = self.score_presence(structured_claims, unstructured_claims)
        detail = self.score_detail(structured_claims, unstructured_claims)
        evidence = self.score_evidence(signals)
        confirmation = self.score_confirmation(structured_claims, signals)

        score = (
            self.w_presence * presence +
            self.w_detail * detail +
            self.w_evidence * evidence +
            self.w_confirmation * confirmation
        )
        return clamp(score)

    def _to_float(self, s: str) -> Optional[float]:
        if s is None:
            return None
        ss = s.strip().replace("%", "")
        try:
            return float(ss)
        except ValueError:
            return None

    # -------------------
    # Evidence & confirmation signals from README text
    # -------------------
    def evidence_signals(self, readme_text: str) -> Dict[str, bool]:
        t = (readme_text or "").lower()

        # evidence sections
        has_evidence_section = any(h in t for h in EVIDENCE_SECTION_HINTS)

        # authoritative links
        confirming = False
        found_domains = []
        for dom in CONFIRMING_DOMAINS:
            if dom in t:
                confirming = True
                found_domains.append(dom)

        # mentions of seeds/hardware/reproducible setup
        has_setup = any(k in t for k in ["seed", "random seed", "gpu", "hardware", "a100", "v100", "cpu", "epochs", "batch size", "learning rate", "eval"])

        return {
            "has_evidence_section": has_evidence_section,
            "has_setup": has_setup,
            "has_confirming_links": confirming,
            "confirming_domains_present": bool(found_domains),
        }

    # -------------------
    # Scoring
    # -------------------
    def score_presence(self, claims_structured: List, claims_unstructured: List) -> float:
        return 1.0 if (claims_structured or claims_unstructured) else 0.0

    def score_detail(self, claims_structured: List, claims_unstructured: List) -> float:
        """
        Heuristic:
        - Full detail if we have at least one structured claim (dataset+metric+value+context).
        - Otherwise, award partial credit for README claims with metric+value and recognizable benchmark.
        """
        if claims_structured:
            # Count context fields present
            ctx_hits = 0
            ctx_total = 0
            for (_, _, _, extra) in claims_structured[:5]:  # sample a few
                ctx_total += 2
                if extra.get("split"): ctx_hits += 1
                if extra.get("task"): ctx_hits += 1
            # base detail for having structured claims
            base = 0.7
            ctx_boost = (ctx_hits / max(1, ctx_total)) * 0.3
            return clamp(base + ctx_boost)

        if claims_unstructured:
            # Has metric+value+benchmark, but no structured context
            return 0.5

        return 0.0

    def score_evidence(self, signals: Dict[str, bool]) -> float:
        pts = 0.0
        if signals.get("has_evidence_section"): pts += 0.4
        if signals.get("has_setup"): pts += 0.3
        if signals.get("has_confirming_links") or signals.get("confirming_domains_present"): pts += 0.3
        return clamp(pts)

    def score_confirmation(self, claims_structured: List, signals: Dict[str, bool]) -> float:
        """
        Strong confirmation if:
        - There are numeric results in model-index (structured), OR
        - README has claims AND links to authoritative leaderboards/papers.
        """
        if claims_structured:
            return 1.0
        if signals.get("has_confirming_links") or signals.get("confirming_domains_present"):
            return 0.7
        return 0.0

    # -------------------
    # Public API
    # -------------------
    def compute(self, url: str, hf_token: Optional[str] = None) -> float:
        """
        Overall score in [0,1] combining:
        presence, detail, evidence, confirmation.
        """
        repo_id = self.url_to_repo_id(url)
        info = self.get_model_info(repo_id, token=hf_token)

        # Structured
        structured_claims = self.extract_model_index_claims(info)

        # README text
        readme_text = ""
        # ModelInfo.card is a huggingface_hub object; safe to access .content
        if getattr(info, "card", None) is not None:
            readme_text = info.card.content or ""

        # Unstructured
        unstructured_claims = self.extract_readme_claims(readme_text)

        # Evidence/confirmation signals
        signals = self.evidence_signals(readme_text)

        # Subscores
        presence = self.score_presence(structured_claims, unstructured_claims)
        detail = self.score_detail(structured_claims, unstructured_claims)
        evidence = self.score_evidence(signals)
        confirmation = self.score_confirmation(structured_claims, signals)

        score = (
            self.w_presence * presence +
            self.w_detail * detail +
            self.w_evidence * evidence +
            self.w_confirmation * confirmation
        )
        return clamp(score)

    # Optional: for debugging/explanations
    def explain(self, url: str, hf_token: Optional[str] = None) -> Dict[str, Any]:
        repo_id = self.url_to_repo_id(url)
        info = self.get_model_info(repo_id, token=hf_token)
        structured = self.extract_model_index_claims(info)
        readme_text = info.card.content if getattr(info, "card", None) else ""
        unstructured = self.extract_readme_claims(readme_text)
        signals = self.evidence_signals(readme_text)
        return {
            "structured_claims_sample": structured[:5],
            "unstructured_claims_sample": unstructured[:5],
            "signals": signals,
            "presence": self.score_presence(structured, unstructured),
            "detail": self.score_detail(structured, unstructured),
            "evidence": self.score_evidence(signals),
            "confirmation": self.score_confirmation(structured, signals),
        }

if __name__ == "__main__":
    metric = PerformanceClaimMetric()
    tests = [
        "https://huggingface.co/google-bert/bert-base-uncased",
        "https://huggingface.co/openai/whisper-tiny",
        # add a repo you know has a 'model-index' or benchmark tables in README
        "https://huggingface.co/tiiuae/falcon-7b",
        "https://huggingface.co/EleutherAI/gpt-neox-20b",
    ]
    for u in tests:
        try:
            s = metric.compute(u, hf_token=os.getenv("HF_TOKEN"))
            print(f"{u} -> {s:.3f}")
        except Exception as e:
            print("Error:", u, e)

