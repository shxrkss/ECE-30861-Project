from urllib.parse import urlparse

# -------------------
# Helper function to get owner and repo name from GitHub URL
# -------------------
def parse_github_url(url):
    try:
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        # A valid GitHub repo URL path should have at least 2 parts: owner and repo_name
        if len(path_parts) >= 2:
            owner = path_parts[0]
            repo_name = path_parts[1]
            return owner, repo_name
        else:
            return None, None
            
    except Exception:
        return None, None

def clamp(n):
    return max(0, min(n, 1))