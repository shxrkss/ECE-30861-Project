from urllib.parse import urlparse
import requests
from typing import Tuple, Dict

# -------------------
# Helper function to get the ID from a URL
# -------------------
def extract_model_or_dataset_id(url: str) -> str:
    # Extract the path, remove leading/trailing slashes, split by '/'
    path_parts = urlparse(url).path.strip('/').split('/')

    if len(path_parts) < 2:
        raise ValueError(f"Invalid URL, can't extract model/dataset ID: {url}")
    return "/".join(path_parts[:2])

# -------------------
# Helper function to get number of repo commits from huggingface api for bus factor
# -------------------
def get_repo_commits(url: str) -> Tuple[int, int, Dict[str, int]]:
    if "/datasets/" in url:
        repo_type: str = "datasets"
    else:
        repo_type = "models"

    # Extract repo_id from URL
    repo_id: str = extract_model_or_dataset_id(url)
    
    # API endpoint for commits
    api_url: str = f"https://huggingface.co/api/{repo_type}/{repo_id}/commits"
    response = requests.get(api_url)
    response.raise_for_status()
    commits: list[dict] = response.json()

    # total commits
    C: int = len(commits)

    # aggregate by author
    contrib_counts: Dict[str, int] = {}
    for commit in commits:
        author: str = commit["author"]["name"]
        contrib_counts[author] = contrib_counts.get(author, 0) + 1

    # total contributors
    N: int = len(contrib_counts)
    ci: Dict[str, int] = contrib_counts

    return N, C, ci