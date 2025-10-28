# license_metric.py
from __future__ import annotations
import re
from typing import Optional, Set, Tuple
from urllib.parse import urlparse
import os
import time
from huggingface_hub import HfApi
from src.metrics.base import MetricBase ##################################################333 metrics.base
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import logging
from log import setup_logging

# Common license aliases -> canonical SPDX-ish keys (extend as needed)
LICENSE_NORMALIZATION = {
    # Permissive
    "mit": "mit",
    "apache-2.0": "apache-2.0",
    "apache 2.0": "apache-2.0",
    "bsd-3-clause": "bsd-3-clause",
    "bsd 3-clause": "bsd-3-clause",
    "bsd-2-clause": "bsd-2-clause",
    "bsd 2-clause": "bsd-2-clause",
    "mpl-2.0": "mpl-2.0",
    "mpl 2.0": "mpl-2.0",
    "lgpl-3.0": "lgpl-3.0",
    "lgpl 3.0": "lgpl-3.0",
    # Copyleft / others
    "gpl-3.0": "gpl-3.0",
    "gpl 3.0": "gpl-3.0",
    "agpl-3.0": "agpl-3.0",
    "agpl 3.0": "agpl-3.0",
    # Creative Commons (often for datasets / model weights)
    "cc-by-4.0": "cc-by-4.0",
    "cc-by 4.0": "cc-by-4.0",
    "cc-by-sa-4.0": "cc-by-sa-4.0",
    "cc-by-sa 4.0": "cc-by-sa-4.0",
    "cc-by-nc-4.0": "cc-by-nc-4.0",
    "cc-by-nc 4.0": "cc-by-nc-4.0",
    "cc-by-nc-sa-4.0": "cc-by-nc-sa-4.0",
    "cc-by-nc-sa 4.0": "cc-by-nc-sa-4.0",
    # Hugging Face / custom family (decide policy!)
    "llama2": "llama2",
    "llama 2": "llama2",
    "llama-2": "llama2",
    "llama3": "llama3",
    "llama 3": "llama3",
    "llama-3": "llama3",
    "meta-llama license": "llama2",  # treat as llama2-style
    "meta llama license": "llama2",
    "meta-llama-3 license": "llama3",
    # Fallback
    "other": "other",
    "unknown": "unknown",
}

# Regex to find license-like statements in README (SPDX IDs + common names)
LICENSE_REGEX = re.compile(
    r"""
    (?:
        license[:\s]*  # 'License:' prefix (optional but common)
    )?
    (
        apache[-\s]?2\.0
        |mit
        |bsd[-\s]?2[-\s]?clause
        |bsd[-\s]?3[-\s]?clause
        |mpl[-\s]?2\.0
        |lgpl[-\s]?3\.0
        |gpl[-\s]?3\.0
        |agpl[-\s]?3\.0
        |cc[-\s]?by(?:[-\s]?nc)?(?:[-\s]?sa)?[-\s]?4\.0
        |llama[-\s]?2
        |llama[-\s]?3
        |meta[-\s]?llama(?:[-\s]?3)?
        |other
        |unknown
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


class LicenseMetric(MetricBase):
    def __init__(self) -> None:
        super().__init__("license")

    # --- URL -> repo_id ---
    def url_to_repo_id(self, url: str) -> str:
        p = urlparse(url)
        parts = [s for s in p.path.split("/") if s]
        if not parts:
            raise ValueError(f"Invalid HF URL: {url}")
        return parts[0] if len(parts) == 1 else "/".join(parts[:2])

    # --- Hub calls ---
    def get_model_info(self, repo_id: str, token: Optional[str] = None):
        # expand tags/cardData to maximize chances of seeing license metadata
        return HfApi().model_info(repo_id, token=token, expand=["cardData", "tags"])

    def get_readme_text(self, repo_id: str, token: Optional[str] = None) -> str:
        try:
            mc = HfApi().model_card(repo_id, token=token)
            return (mc.content or "") if mc else ""
        except Exception:
            return ""

    # --- Extraction & normalization ---
    def normalize(self, raw: str) -> Optional[str]:
        if not raw:
            return None
        s = raw.strip().lower()
        s = s.replace("_", "-")
        s = re.sub(r"\s+", " ", s)

        # unify a few patterns
        s = s.replace("apache license", "apache")
        s = s.replace("version", "").strip()

        # try direct map
        if s in LICENSE_NORMALIZATION:
            return LICENSE_NORMALIZATION[s]

        # try stripping punctuation/space variants
        s2 = s.replace(" ", "").replace("-", " ").strip()
        if s2 in LICENSE_NORMALIZATION:
            return LICENSE_NORMALIZATION[s2]

        # SPDX-like shorteners
        if s.startswith("apache") and "2.0" in s:
            return "apache-2.0"
        if s.startswith("bsd 3"):
            return "bsd-3-clause"
        if s.startswith("bsd 2"):
            return "bsd-2-clause"
        if s.startswith("mpl") and "2.0" in s:
            return "mpl-2.0"
        if s.startswith("lgpl") and "3.0" in s:
            return "lgpl-3.0"
        if s.startswith("gpl") and "3.0" in s:
            return "gpl-3.0"
        if s.startswith("agpl") and "3.0" in s:
            return "agpl-3.0"
        if "llama-3" in s or "llama 3" in s:
            return "llama3"
        if "llama-2" in s or "llama 2" in s or "meta-llama" in s:
            return "llama2"

        # CC patterns
        cc = re.search(r"cc[-\s]?by(?:[-\s]?nc)?(?:[-\s]?sa)?[-\s]?4\.0", s)
        if cc:
            return cc.group(0).lower().replace(" ", "").replace("_", "-")

        # couldn't normalize
        return None

    def extract_from_metadata(self, info) -> Optional[str]:
        # 1) explicit field
        # huggingface_hub exposes .license if present
        lic = getattr(info, "license", None)
        if isinstance(lic, str):
            norm = self.normalize(lic)
            if norm:
                return norm

        # 2) tags like 'license:apache-2.0'
        tags = getattr(info, "tags", None) or []
        for t in tags:
            if isinstance(t, str) and t.lower().startswith("license:"):
                norm = self.normalize(t.split(":", 1)[1])
                if norm:
                    return norm

        # 3) YAML front matter cardData.license
        card = getattr(info, "cardData", None) or {}
        raw = card.get("license")
        if isinstance(raw, str):
            norm = self.normalize(raw)
            if norm:
                return norm

        return None

    def extract_from_readme(self, readme_text: str) -> Optional[str]:
        if not readme_text:
            return None
        # Try a few matches; pick the first normalized hit
        for m in LICENSE_REGEX.finditer(readme_text):
            norm = self.normalize(m.group(1))
            if norm:
                return norm
        # Also catch lines like "License: Apache-2.0"
        m2 = re.search(r"license[:\s]+([^\n\r]+)", readme_text, re.I)
        if m2:
            norm = self.normalize(m2.group(1))
            if norm:
                return norm
        return None

    # --- Scoring (binary) ---
    def compute(self, url: str, allowed: Set[str], hf_token: Optional[str] = None) -> Tuple[float, int]:
        """
        Returns 1.0 if the model license is in `allowed` (after normalization), else 0.0.
        `allowed` should contain normalized keys (e.g., {'mit','apache-2.0','bsd-3-clause', ...}).
        """
        setup_logging()

        start = time.time()
        logging.critical("Starting License Metric")

        repo_id = self.url_to_repo_id(url)
        info = self.get_model_info(repo_id, token=hf_token)

        # 1) metadata path
        norm = self.extract_from_metadata(info)
        logging.info("Extracting metadata")

        # 2) fallback to README
        if not norm:
            readme = self.get_readme_text(repo_id, token=hf_token)
            norm = self.extract_from_readme(readme)
        logging.info("Used README instead")

        # If still unknown, treat as not permitted
        if not norm:
            end = time.time()
            latency = (end - start) * 1000
            latency = int(latency)
            logging.critical("Treating license as not permitted") # info
            logging.critical("Finished License Metric, with latency")
            return 0.0, latency
        
        end = time.time()
        latency = (end - start) * 1000
        latency = int(latency)

        logging.critical("Finished License Metric, with latency")

        if norm in allowed:
            return 1.0, latency
        
        return 0.0, latency

if __name__ == "__main__":
    metric = LicenseMetric()

    # ACME's allow-list (normalized). Adjust to your policy.
    allowed = {
        "mit",
        "apache-2.0",
        "bsd-2-clause",
        "bsd-3-clause",
        "mpl-2.0",
        # decide on these per company policy:
        # "cc-by-4.0",   # often okay for weights with attribution
        # "lgpl-3.0",    # weak copyleft – often okay for linking
        # Explicitly EXCLUDE strong copyleft, NC, and custom LLaMA unless approved:
        # (so don't include "gpl-3.0","agpl-3.0","cc-by-nc-4.0","llama2","llama3")
    }

    urls = [
        "https://huggingface.co/google-bert/bert-base-uncased",
        "https://huggingface.co/openai/whisper-tiny",
        "https://huggingface.co/meta-llama/Llama-2-7b",   # likely 'llama2' (custom)
    ]

    for u in urls:
        try:
            score, latency = metric.compute(u, allowed=allowed, hf_token=os.getenv("HF_TOKEN"))
            print("score: ", score)
            print("latency: ", latency)
        except Exception as e:
            print("Error:", u, e)
