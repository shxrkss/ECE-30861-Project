from metrics.base import MetricBase
from huggingface_hub import snapshot_download
from typing import Tuple, Optional
from urllib.parse import urlparse
import os
import time
import sys
import tempfile
import subprocess
import glob
import contextlib
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import logging
from log import setup_logging

import warnings
warnings.filterwarnings("ignore", category=UserWarning)


class CodeQualityMetric(MetricBase):
    def __init__(self) -> None:
        super().__init__("code_quality")

    def compute(self, code_url: Optional[str], model_url: Optional[str] = None) -> Tuple[float, int]:
        """
        Computes the code quality metric for a given code repository URL or model URL.
        Args:
            code_url: URL to the code repository (e.g., GitHub)
            model_url: Optional URL to the model repository (e.g., HuggingFace)

        Returns:
            A tuple containing:
                - A normalized score between 0.0 and 1.0 (higher is better)
                - Latency in milliseconds taken to compute the metric
        """
        setup_logging()

        start = time.time()
        logging.critical("Starting Code Quality Metric")

        repo_url = code_url or model_url
        if not repo_url:
            print("No code or model URL provided.", file=sys.stderr)
            logging.critical("Unable to find URL")
            return 0.0, int((time.time() - start) * 1000)

        # Determine clone URL
        parsed = urlparse(repo_url)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) < 2:
            print("Invalid URL format.", file=sys.stderr)
            return 0.0, int((time.time() - start) * 1000)
        
        host = parsed.netloc
        owner, repo = path_parts[0], path_parts[1]

        total_violations = 0
        file_count = 0
        total_lines = 0

        logging.info("Accessing code")
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                if "github.com" in host:
                    # Clone GitHub repo (shallow clone for speed)
                    clone_url = f"https://github.com/{owner}/{repo}.git"
                    subprocess.run(
                        ["git", "clone", "--depth", "1", clone_url, tmpdir],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=30
                    )
                elif "huggingface.co" in host:
                    # Download HuggingFace model repo snapshot 
                    with contextlib.redirect_stdout(open(os.devnull, "w")), contextlib.redirect_stderr(open(os.devnull, "w")):
                        snapshot_download(
                            repo_id=f"{owner}/{repo}",
                            repo_type="model",
                            local_dir=tmpdir,
                            ignore_patterns=["*.bin", "*.pt", "*.onnx", "*.jpg", "*.png", "*.pdf"]
                        )
                else:
                    # If host is not supported, exit
                    print(f"Unsupported host: {host}", file=sys.stderr)
                    return 0.0, int((time.time() - start) * 1000)
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                return 0.0, int((time.time() - start) * 1000)
            
            # Adjust repo_root if extracted repo has a single top-level folder
            repo_root = tmpdir
            contents = os.listdir(tmpdir)
            if len(contents) == 1 and os.path.isdir(os.path.join(tmpdir, contents[0])):
                repo_root = os.path.join(tmpdir, contents[0])

            py_files = glob.glob(os.path.join(repo_root, "**", "*.py"), recursive=True)

            for filepath in py_files:
                if not os.path.exists(filepath):
                    print(f"Warning: File missing before linting: {filepath}", file=sys.stderr)
                    continue
                try:
                    # use flake8 to count violations and line count
                    result = subprocess.run(
                        [sys.executable, "-m", "flake8", "--select=F,E9", "--max-line-length=120", filepath],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    violations = len(result.stdout.splitlines())
                    total_violations += violations
                    file_count += 1

                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        total_lines += sum(1 for _ in f)

                except Exception as e:
                    print(f"Warning: Error linting {filepath}: {e}", file=sys.stderr)

        # Normalize score: 0 violations = 1.0, 20+ violations per 100 lines = 0.0
        logging.info("Normalizing score")
        if file_count == 0:
            normalized_score = 0.0 # if no code, no score
        else:
            violations_per_1000_lines = (total_violations / total_lines) * 1000
            penalty = min(violations_per_1000_lines / 20, 1.0)
            normalized_score = max(0.0, 1.0 - penalty)

        latency = int((time.time() - start) * 1000)
        logging.critical("Finished Code Quality Metric, with latency")

        return round(normalized_score, 2), latency

    def is_applicable(self, code_url) -> bool:
        """
        Determines if the metric is applicable based on the presence of a code URL.

        Args:
            code_url: URL to the code repository (e.g., GitHub)

        Returns:
            True if code_url is provided, False otherwise.
        """
        if code_url:
            return True
        
        return False

# -------------------
# Example code snippet that shows how to use the code quality metric
# -------------------
if __name__ == "__main__":
    # huggingface url: https://huggingface.co/parvk11/audience_classifier_model
    # github url: https://github.com/google-research/bert
    url = "https://huggingface.co/parvk11/audience_classifier_model"
    metric = CodeQualityMetric()
    code_score, latency = metric.compute(url)
    
    if code_score is not None:
        print(f"Code quality score for {url}: {code_score:.4f}, with latency of {latency} ms")
    else:
        print(f"Could not compute code quality score for {url}")
