import sys

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