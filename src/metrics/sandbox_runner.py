# src/metrics/sandbox_runner.py
import subprocess
import tempfile
import os
import shutil
from typing import Tuple

def run_metric_in_sandbox(command: list, timeout: int = 30) -> Tuple[int, str, str]:
    """
    Run a metric command in a sandboxed subprocess with:
    - a temporary working directory
    - no inherited environment variables by default (you can pass a minimal env)
    - timeout enforced
    Returns (returncode, stdout, stderr)
    """
    workdir = tempfile.mkdtemp(prefix="metric_sandbox_")
    try:
        # minimal env - remove secrets
        safe_env = {
            "PATH": os.environ.get("PATH", ""),
            # add other safe env variables if needed
        }
        proc = subprocess.run(command, cwd=workdir, env=safe_env, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    finally:
        try:
            shutil.rmtree(workdir)
        except Exception:
            pass
