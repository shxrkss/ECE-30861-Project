import sys
from pathlib import Path
import subprocess

# -------------------
#  Function to install dependencies from requirements.txt
# -------------------
def install_requirements(req_path: Path = None) -> int:
    if req_path is None:
        # assume requirements.txt is in project root (one level up from src)
        req_path = Path(__file__).resolve().parent.parent / "requirements.txt"

    if not req_path.exists():
        print(f"Error: requirements file not found at {req_path}", file=sys.stderr)
        return 1

    print(f"Installing dependencies from {req_path} using {sys.executable} -m pip ...")
    try:
        # Use the same Python interpreter's pip to ensure correct environment
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
        print(f"Unexpected error during install: {e}", file=sys.stderr)
        return 1

def read_url_file(file_path: str):
    """
    Parses the input file line-by-line.
    Each line: code_link, dataset_link, model_link
    Returns:
        model_info: List of tuples (model_link, code_link or None, dataset_link or None)
    """
    datasets_seen = set()
    model_info = []

    with open(file_path, "r") as f:
        for line_num, line in enumerate(f, 1):
            parts = line.strip().split(",", maxsplit=2)
            if len(parts) != 3:
                print(f"Warning: Line {line_num} does not have 3 comma-separated fields: {line.strip()}", file=sys.stderr)
                continue

            code_link, dataset_link, model_link = [p.strip() for p in parts]

            if not model_link:
                print(f"Warning: Line {line_num} missing model_link (skipping line)", file=sys.stderr)
                continue

            # Handle dataset deduplication
            if dataset_link and dataset_link in datasets_seen:
                dataset_link = None
            elif dataset_link:
                datasets_seen.add(dataset_link)

            code_link = code_link if code_link else None
            dataset_link = dataset_link if dataset_link else None

            model_info.append((model_link, code_link, dataset_link))

    return model_info

def main():
    if len(sys.argv) != 2:
        print("Usage: python cli.py <absolute_path_to_url_file>", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        model_info = read_url_file(file_path)
    except FileNotFoundError:
        print(f"Error: File not found - {file_path}", file=sys.stderr)
        sys.exit(1)

    for model_link, code_link, dataset_link in model_info:
        print(f"{model_link}, <{code_link if code_link else 'None'}, {dataset_link if dataset_link else 'None'}>")

if __name__ == "__main__":
    main()