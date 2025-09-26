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