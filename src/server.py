from fastapi import FastAPI
import subprocess
import sys
import json

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "OK"}

@app.post("/run-tests")
def run_tests():
    """Example: trigger your existing test flow."""
    result = subprocess.run(
        [sys.executable, "src/main.py", "test"],
        capture_output=True,
        text=True
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }