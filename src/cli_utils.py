import sys
from pathlib import Path
import subprocess
import os

def install_requirements(req_path: Path = None) -> int:
    """
    Installs dependencies from requirements.txt using pip.
    Args: req_path (Path): Path to the requirements.txt file.
    Returns the pip exit code (0 if success).
    """
    
    if not req_path.exists():
        print(f"Error: requirements file not found at {req_path}", file=sys.stderr)
        return 1

    print(f"Installing dependencies from {req_path} using {sys.executable} -m pip ...")
    try:
        # Run pip install command with subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_path)],
            check=True
        )
        print("Dependencies installed successfully.")
        return 0
    
    except subprocess.CalledProcessError as e:
        print(f"pip install failed with exit code {e.returncode}", file=sys.stderr)
        return e.returncode
    
    except Exception as e:
        # Any other unexpected error during install
        print(f"Unexpected error during install: {e}", file=sys.stderr)
        return 1

def read_url_file(file_path: str):
    """
    Parses the input file line-by-line.
    Each line: code_link, dataset_link, model_link
    Returns:
        model_info: List of tuples (code_link or None, dataset_link or None, model_link)
    """
    model_info = []

    with open(file_path, "r") as f:
        for line_num, line in enumerate(f, 1):
            parts = line.strip().split(",", maxsplit=2)
            if len(parts) != 3:
                print(f"Warning: Line {line_num} does not have 3 comma-separated fields: {line.strip()}", file=sys.stderr)
                continue

            code_link, dataset_link, model_link = [p.strip() for p in parts]

            # No model_link error handling
            if not model_link:
                print(f"Warning: Line {line_num} missing model_link (skipping line)", file=sys.stderr)
                continue

            # Normalize empty strings to None
            code_link = code_link if code_link else None
            dataset_link = dataset_link if dataset_link else None

            model_info.append((code_link, dataset_link, model_link))

    return model_info