import sys
from cli import *

def main():
    if len(sys.argv) != 2:
        print("Usage: python cli.py <absolute_path_to_url_file>", file=sys.stderr)
        sys.exit(1)

    file_path: str = sys.argv[1]

    try:
        model_info = read_url_file(file_path)
    except FileNotFoundError:
        print(f"Error: File not found - {file_path}", file=sys.stderr)
        sys.exit(1)

    for model_link, code_link, dataset_link in model_info:
        print(f"{model_link}, {code_link if code_link else 'None'}, {dataset_link if dataset_link else 'None'}")

if __name__ == "__main__":
    main()