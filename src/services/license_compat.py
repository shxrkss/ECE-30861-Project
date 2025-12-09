# src/services/license_compat.py
import requests
from urllib.parse import urlparse
from typing import Tuple

def _extract_github_owner_repo(github_url: str) -> Tuple[str, str]:
    p = urlparse(github_url)
    parts = [segment for segment in p.path.strip("/").split("/") if segment]
    if len(parts) < 2:
        raise ValueError("Cannot parse owner/repo from GitHub URL")
    return parts[0], parts[1]


def get_github_license_spdx(github_url: str, token: str | None = None) -> str | None:
    owner, repo = _extract_github_owner_repo(github_url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    resp = requests.get(api_url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    lic = data.get("license") or {}
    return lic.get("spdx_id")  # e.g., "MIT", "Apache-2.0", "GPL-3.0-or-later"


def get_hf_model_license(model_id: str) -> str | None:
    api_url = f"https://huggingface.co/api/models/{model_id}"
    resp = requests.get(api_url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    # HF usually returns an array of licenses or a single string
    lic = data.get("license")
    if isinstance(lic, list) and lic:
        return lic[0]
    return lic


def assess_compatibility(model_license: str | None, github_license: str | None) -> Tuple[bool, str]:
    """
    Very simplified compatibility check. You can enrich this based on ModelGo.
    """
    if not model_license or not github_license:
        return False, "Missing license information"

    permissive = {"MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "MPL-2.0"}
    strong_copyleft = {"GPL-3.0", "GPL-2.0", "AGPL-3.0"}

    if model_license in permissive and github_license in permissive:
        return True, "Both model and code use permissive licenses"
    if model_license in strong_copyleft or github_license in strong_copyleft:
        return False, "Strong copyleft involved; fine-tune+inference may require open-sourcing combined work"

    # Fallback: assume compatible but warn
    return True, "Licenses appear compatible, but this assessment is conservative and should be reviewed"
