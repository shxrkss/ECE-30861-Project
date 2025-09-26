# # code_quality_metric.py
# from __future__ import annotations
# import os, re, io, tempfile
# from typing import Optional, Dict, Any, List, Tuple
# from urllib.parse import urlparse

# from base import MetricBase
# from utils.tools import clamp

# from huggingface_hub import snapshot_download
# from radon.metrics import mi_visit
# from radon.complexity import cc_visit
# import pycodestyle

# # Optional pylint integration (set USE_PYLINT=True to enable)
# USE_PYLINT = False
# try:
#     if USE_PYLINT:
#         from pylint.lint import Run as PylintRun
# except Exception:
#     USE_PYLINT = False  # fallback if pylint not installed

# def _url_to_repo_id(url: str) -> str:
#     p = urlparse(url)
#     parts = [s for s in p.path.split("/") if s]
#     if not parts:
#         raise ValueError(f"Invalid HF URL: {url}")
#     return parts[0] if len(parts) == 1 else "/".join(parts[:2])

# def _download_repo_py(repo_id: str, hf_token: Optional[str]) -> str:
#     """
#     Download only Python files to a temp dir to speed things up.
#     """
#     tmp = tempfile.mkdtemp(prefix="hf-codeq-")
#     snapshot_download(
#         repo_id,
#         token=hf_token,
#         repo_type="model",
#         local_dir=tmp,
#         local_dir_use_symlinks=False,
#         allow_patterns=["*.py", "examples/*.py", "scripts/*.py", "src/**/*.py"]
#     )
#     return tmp

# def _iter_python_files(root: str) -> List[str]:
#     out: List[str] = []
#     for dirpath, _, filenames in os.walk(root):
#         for f in filenames:
#             if f.endswith(".py"):
#                 out.append(os.path.join(dirpath, f))
#     return out

# def _read_text(path: str) -> str:
#     try:
#         with io.open(path, "r", encoding="utf-8") as fh:
#             return fh.read()
#     except UnicodeDecodeError:
#         # try latin-1 as worst-case fallback
#         with io.open(path, "r", encoding="latin-1") as fh:
#             return fh.read()
#     except Exception:
#         return ""

# def _loc(text: str) -> int:
#     return sum(1 for _ in text.splitlines())

# def _pycodestyle_errors(path: str) -> int:
#     try:
#         checker = pycodestyle.Checker(filename=path, show_source=False, quiet=True)
#         return checker.check_all()
#     except Exception:
#         return 0  # fail-open

# def _pylint_score(paths: List[str]) -> Optional[float]:
#     """
#     Returns global pylint score in [0,10], or None if pylint disabled/unavailable.
#     """
#     if not USE_PYLINT:
#         return None
#     try:
#         # PylintRun writes to stdout; exit=False prevents sys.exit
#         results = PylintRun([*paths, "--disable=R,C"], exit=False)  # ignore refactor/convention if desired
#         # Newer pylint exposes linter.stats.global_note; fallback to parsing if needed
#         try:
#             note = results.linter.stats.get("global_note", None)
#             return float(note) if note is not None else None
#         except Exception:
#             return None
#     except Exception:
#         return None

# def _complexity_score(avg_cc: float) -> float:
#     """
#     Map average cyclomatic complexity to [0,1].
#     ~5 => ~1.0 (simple), 25+ => ~0.0 (very complex).
#     """
#     return clamp(1.0 - max(0.0, (avg_cc - 5.0)) / 20.0)

# def _style_score(errors: int, lines: int) -> float:
#     """
#     Style score from pycodestyle violations per line.
#     Allow ~5% violations without heavy penalty.
#     """
#     if lines <= 0:
#         return 1.0
#     ratio = errors / max(1.0, lines)  # violations per line
#     return clamp(1.0 - ratio / 0.05)  # 0.05 ≈ 5% lines having an issue

# class CodeQualityMetric(MetricBase):
#     """
#     Code quality = weighted blend of:
#       - Maintainability Index (radon)        [40%]
#       - Style conformance (pycodestyle)      [30%]
#       - Cyclomatic complexity (radon cc)     [30%]
#     Optional: incorporate pylint global note as a small boost.
#     """
#     def __init__(self,
#                  w_mi: float = 0.40,
#                  w_style: float = 0.30,
#                  w_complexity: float = 0.30) -> None:
#         super().__init__("code_quality")
#         self.w_mi = w_mi
#         self.w_style = w_style
#         self.w_complexity = w_complexity

#     def compute(self, url: str, hf_token: Optional[str] = None) -> float:
#         repo_id = _url_to_repo_id(url)
#         local_dir = _download_repo_py(repo_id, hf_token)

#         py_files = _iter_python_files(local_dir)
#         if not py_files:
#             return 0.0  # no python code to evaluate

#         total_loc = 0
#         sum_mi = 0.0
#         sum_style = 0.0
#         all_cc: List[float] = []

#         # Per-file analysis, weighted by LOC
#         for path in py_files:
#             text = _read_text(path)
#             if not text.strip():
#                 continue

#             lines = _loc(text)
#             total_loc += lines

#             # Maintainability Index (0..100) -> [0,1]
#             try:
#                 mi = mi_visit(text, multi=False)
#                 mi01 = clamp(mi / 100.0)
#             except Exception:
#                 mi01 = 0.5  # neutral fallback

#             # Cyclomatic complexity: average over blocks
#             try:
#                 blocks = cc_visit(text)
#                 if blocks:
#                     avg_cc = sum(b.complexity for b in blocks) / len(blocks)
#                 else:
#                     avg_cc = 1.0
#             except Exception:
#                 avg_cc = 10.0  # neutral-ish fallback

#             # Style violations
#             try:
#                 errs = _pycodestyle_errors(path)
#             except Exception:
#                 errs = 0

#             style01 = _style_score(errs, lines)
#             comp01 = _complexity_score(avg_cc)

#             # accumulate weighted by file size
#             sum_mi += mi01 * lines
#             sum_style += style01 * lines
#             all_cc.append((comp01, lines))

#         if total_loc <= 0:
#             return 0.0

#         mi_mean = sum_mi / total_loc
#         style_mean = sum_style / total_loc
#         comp_mean = (sum(c * w for c, w in all_cc) / total_loc) if all_cc else 1.0

#         score = self.w_mi * mi_mean + self.w_style * style_mean + self.w_complexity * comp_mean

#         # Optional pylint boost (small nudge, capped)
#         if USE_PYLINT:
#             pyl = _pylint_score(py_files)
#             if pyl is not None:
#                 boost = clamp(pyl / 10.0)  # 0..1 from pylint's 0..10
#                 score = clamp(0.9 * score + 0.1 * boost)

#         return clamp(score)

#     # Helpful for dashboards / debugging
#     def explain(self, url: str, hf_token: Optional[str] = None) -> Dict[str, Any]:
#         repo_id = _url_to_repo_id(url)
#         local_dir = _download_repo_py(repo_id, hf_token)
#         py_files = _iter_python_files(local_dir)

#         if not py_files:
#             return {"files": 0, "total_loc": 0, "mi_mean": 0, "style_mean": 0, "comp_mean": 0, "score": 0}

#         total_loc = 0
#         sum_mi = 0.0
#         sum_style = 0.0
#         all_cc: List[Tuple[float, int]] = []
#         per_file: List[Dict[str, Any]] = []

#         for path in py_files:
#             text = _read_text(path)
#             if not text.strip():
#                 continue
#             lines = _loc(text)
#             total_loc += lines

#             try:
#                 mi = mi_visit(text, multi=False)
#                 mi01 = clamp(mi / 100.0)
#             except Exception:
#                 mi01 = 0.5

#             try:
#                 blocks = cc_visit(text)
#                 avg_cc = (sum(b.complexity for b in blocks) / len(blocks)) if blocks else 1.0
#             except Exception:
#                 avg_cc = 10.0

#             errs = _pycodestyle_errors(path)
#             style01 = _style_score(errs, lines)
#             comp01 = _complexity_score(avg_cc)

#             per_file.append({
#                 "path": os.path.relpath(path, local_dir),
#                 "loc": lines,
#                 "mi_0_1": round(mi01, 3),
#                 "avg_cc": round(avg_cc, 2),
#                 "style_errors": int(errs),
#                 "style_0_1": round(style01, 3),
#                 "complexity_0_1": round(comp01, 3),
#             })

#             sum_mi += mi01 * lines
#             sum_style += style01 * lines
#             all_cc.append((comp01, lines))

#         mi_mean = sum_mi / total_loc
#         style_mean = sum_style / total_loc
#         comp_mean = (sum(c * w for c, w in all_cc) / total_loc) if all_cc else 1.0
#         score = clamp(self.w_mi * mi_mean + self.w_style * style_mean + self.w_complexity * comp_mean)

#         if USE_PYLINT:
#             pyl = _pylint_score(py_files)
#             if pyl is not None:
#                 score = clamp(0.9 * score + 0.1 * clamp(pyl / 10.0))

#         return {
#             "files": len(py_files),
#             "total_loc": total_loc,
#             "mi_mean": round(mi_mean, 3),
#             "style_mean": round(style_mean, 3),
#             "comp_mean": round(comp_mean, 3),
#             "score": round(score, 3),
#             "per_file": per_file[:50],  # truncate for brevity
#         }

# if __name__ == "__main__":
#     metric = CodeQualityMetric()
#     urls = [
#         "https://huggingface.co/google-bert/bert-base-uncased",
#         "https://huggingface.co/tiiuae/falcon-7b",
#     ]
#     for u in urls:
#         try:
#             score = metric.compute(u, hf_token=os.getenv("HF_TOKEN"))
#             print(f"{u} -> code_quality={score:.3f}")
#             # print(metric.explain(u, hf_token=os.getenv("HF_TOKEN")))
#         except Exception as e:
#             print("Error:", u, e)
##########################################################################################################
from src.metrics.base import MetricBase
from src.metrics.utils.tools import parse_github_url
from dotenv import load_dotenv
from github import Github
import os

class CodeQualityMetric(MetricBase):
    def __init__(self, name: str) -> None:
        super().__init__("code_quality")

    def compute(self, code_url) -> float:
        load_dotenv()
        token = os.getenv("GITHUB_TOKEN")

        if CodeQualityMetric.is_applicable(code_url):
            owner, repo_name = parse_github_url(code_url)
    
            if not owner or not repo_name:
                return "Error: Invalid GitHub URL provided."

            g = Github(token)
            try:
                repo = g.get_repo(f"{owner}/{repo_name}")
            except Exception as e:
                return f"Error: Could not access repository. Details: {e}"

            # Define weights for each metric.
            WEIGHTS = {
                "code_scanning": 0.5,
                "contributors": 0.5
            }

            # 1. Code Scanning Factor (Fastest)
            code_scanning_factor = 1.0
            try:
                alerts = repo.get_code_scanning_alerts()
                num_alerts = alerts.totalCount
                code_scanning_factor = max(0, 1 - (num_alerts / 50.0))
            except Exception:
                pass

            # 2. Contributor Factor (Relatively Fast with Pagination)
            contributor_factor = 0.0
            try:
                contributors = repo.get_contributors(anon=True)
                num_contributors = contributors.totalCount
                contributor_factor = min(1.0, num_contributors / 25.0)
            except Exception:
                pass

            # Calculate the final score
            final_score = (
                (WEIGHTS["code_scanning"] * code_scanning_factor) +
                (WEIGHTS["contributors"] * contributor_factor)
            )

            return round(final_score, 2)

        return 0

    def is_applicable(self, code_url) -> bool:
        if code_url:
            return True
        
        return False