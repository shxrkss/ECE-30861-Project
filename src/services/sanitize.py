# src/services/sanitize.py
import re
from urllib.parse import urlparse

URL_RE = re.compile(r"https?://[^\s'\"<>]+")

def redact_urls(text: str) -> str:
    """Replace URLs with [REDACTED_URL] to avoid leaking private endpoints."""
    return URL_RE.sub("[REDACTED_URL]", text)

def validate_and_normalize_github_url(url: str) -> str:
    """Quick sanity check: only allow github.com and api.github.com hosts, returns normalized https URL."""
    try:
        p = urlparse(url)
        host = p.netloc.lower()
        if "github.com" not in host:
            raise ValueError("Only GitHub URLs are allowed for repo fields")
        return f"https://{host}{p.path}"
    except Exception as e:
        raise ValueError("Invalid URL")
