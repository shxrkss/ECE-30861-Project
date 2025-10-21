import time
import re
import subprocess
import tempfile
import logging
import sys
import os
from huggingface_hub import HfApi
from metrics.base import MetricBase
from log import setup_logging

class ReproducibilityMetric(MetricBase):
    """
    Measures how reproducible a HuggingFace model is based on
    whether its demo code runs successfully without modification.
    """

    def __init__(self):
        super().__init__("reproducibility")
        self.hf = HfApi()

    def extract_demo_code(self, repo_id: str) -> str:
        """Fetch README from HuggingFace and extract first Python code block."""
        try:
            card = self.hf.model_info(repo_id).cardData
            if not card or "text" not in card:
                return ""
            content = card["text"]
        except Exception as e:
            logging.warning(f"Could not fetch model card: {e}")
            return ""

        # Find first Python fenced code block
        matches = re.findall(r"```python(.*?)```", content, re.DOTALL)
        if not matches:
            return ""
        return matches[0].strip()

    def try_run_code(self, code: str) -> float:
        """Attempt to execute code snippet safely."""
        if not code:
            return 0.0  # No code provided

        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=20,
                check=True
            )
            logging.info(f"Execution success: {result.stdout[:200]}")
            return 1.0  # runs with no issues
        except subprocess.CalledProcessError as e:
            # Common recoverable issues: missing imports or pip modules
            stderr = e.stderr or ""
            if any(kw in stderr for kw in ["ModuleNotFoundError", "ImportError", "NameError"]):
                logging.warning(f"Recoverable error (debuggable): {stderr[:200]}")
                return 0.5
            else:
                logging.error(f"Execution failed: {stderr[:200]}")
                return 0.0
        except subprocess.TimeoutExpired:
            logging.error("Code execution timed out")
            return 0.0
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    def compute(self, url: str):
        """Compute reproducibility metric given a HuggingFace model URL."""
        setup_logging()
        start = time.time()

        try:
            # Parse repo_id from URL (e.g., huggingface.co/owner/model)
            parts = url.strip("/").split("/")
            repo_id = f"{parts[-2]}/{parts[-1]}" if len(parts) >= 2 else url
            logging.info(f"Computing reproducibility for {repo_id}")

            code = self.extract_demo_code(repo_id)
            if not code:
                self.value = 0.0
            else:
                self.value = self.try_run_code(code)
        except Exception as e:
            logging.error(f"Unexpected error during reproducibility test: {e}")
            self.value = 0.0

        latency = int((time.time() - start) * 1000)
        return self.value, latency


# Example direct test
if __name__ == "__main__":
    metric = ReproducibilityMetric()
    url = "https://huggingface.co/google-bert/bert-base-uncased"
    score, latency = metric.compute(url)
    print(f"Reproducibility score: {score}, latency: {latency} ms")