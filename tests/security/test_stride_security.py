import os
import json
import tempfile
import importlib
from io import BytesIO
from zipfile import ZipFile
import pytest
from fastapi.testclient import TestClient


# ---------- Global app fixture: config env, reload modules, create TestClient ----------

@pytest.fixture(scope="session")
def test_app():
    """
    Builds a TestClient for the FastAPI app with:
    - API key auth configured
    - Dummy AWS bucket
    - Log file path pointing to a temp directory
    - Lowered rate limit for tests
    """
    # --- Environment for auth + bucket + logs + rate limit ---
    os.environ["API_KEYS_JSON"] = json.dumps({
        "testkey": {
            "user": "ore",
            "roles": ["upload", "download", "enumerate", "admin"]
        }
    })
    os.environ["AWS_BUCKET_NAME"] = "dummy-bucket"

    log_dir = tempfile.mkdtemp(prefix="logs_")
    os.environ["LOG_FILE_PATH"] = os.path.join(log_dir, "app.log")

    # small rate limit so we can hit it in tests
    os.environ["RATE_LIMIT_PER_MIN"] = "3"

    # --- Reload modules so they see updated env ---
    import src.services.auth as auth
    import src.log as logmod
    import src.services.rate_limit as rl
    import src.server as server

    importlib.reload(auth)
    importlib.reload(logmod)
    importlib.reload(rl)
    importlib.reload(server)

    app = server.app
    client = TestClient(app)
    return client


# ---------- Helpers to patch S3 service behavior per test ----------

@pytest.fixture
def fake_s3(monkeypatch):
    """
    Monkeypatches src.services.s3_service functions to avoid real AWS calls.
    Allows each test to configure behavior via attributes on the inner object.
    """
    import src.services.s3_service as s3

    state = {
        "manifest": None,
        "checksum": None,
        "download_url": "http://example.com/download",
        "models": [],
        "card_text": "",
    }

    def fake_read_manifest(key: str):
        return state["manifest"]

    def fake_get_checksum(key: str):
        return state["checksum"]

    def fake_presigned_url(key: str, expires_in: int = 300):
        return state["download_url"]

    def fake_list_models(prefix: str = "models/"):
        return state["models"]

    def fake_search_models_by_card(models, regex: str):
        # simplified: just return the models as-is
        return models

    def fake_get_model_card_text(key: str) -> str:
        return state["card_text"]

    monkeypatch.setattr(s3, "read_manifest", fake_read_manifest)
    monkeypatch.setattr(s3, "get_s3_object_checksum", fake_get_checksum)
    monkeypatch.setattr(s3, "generate_presigned_download_url", fake_presigned_url)
    monkeypatch.setattr(s3, "list_s3_models", fake_list_models)
    monkeypatch.setattr(s3, "search_models_by_card", fake_search_models_by_card)
    monkeypatch.setattr(s3, "get_model_card_text", fake_get_model_card_text)

    return state  # tests can mutate state dict


# =====================================================================
# S — Spoofing tests: auth + roles
# =====================================================================

def test_enumerate_requires_auth(test_app):
    resp = test_app.get("/api/enumerate")
    assert resp.status_code in (401, 403), resp.text


def test_enumerate_rejects_invalid_key(test_app):
    resp = test_app.get("/api/enumerate", headers={"X-API-Key": "wrong"})
    # verify_api_key should reject bad key as 401
    assert resp.status_code == 401
    assert "Invalid API key" in resp.text


def test_enumerate_allows_valid_key(test_app, fake_s3):
    # Provide a fake model in S3
    fake_s3["models"] = [
        {"name": "m1", "key": "models/m1.zip", "size": 123, "last_modified": "2025-01-01T00:00:00Z"}
    ]
    fake_s3["card_text"] = "This is a model with https://secret-url.com"

    resp = test_app.get("/api/enumerate", headers={"X-API-Key": "testkey"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1


# =====================================================================
# T — Tampering tests: upload/download integrity
# =====================================================================

def test_download_fails_on_checksum_mismatch(test_app, fake_s3):
    # Manifest + checksum from S3 disagree
    fake_s3["manifest"] = {"checksum": "abc", "filename": "m1.zip"}
    fake_s3["checksum"] = "def"

    resp = test_app.get("/api/download/m1.zip", headers={"X-API-Key": "testkey"})
    assert resp.status_code == 500
    assert "Integrity check failed" in resp.text


def test_download_succeeds_when_checksums_match(test_app, fake_s3):
    fake_s3["manifest"] = {"checksum": "abc", "filename": "m1.zip"}
    fake_s3["checksum"] = "abc"

    resp = test_app.get("/api/download/m1.zip", headers={"X-API-Key": "testkey"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "download_url" in data
    assert data["checksum"] == "abc"


def _make_zip_with_entry(name: str, content: str = "payload") -> bytes:
    buf = BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr(name, content)
    buf.seek(0)
    return buf.getvalue()


def test_upload_rejects_zip_with_traversal_paths(test_app):
    evil_zip = _make_zip_with_entry("../evil.txt", "bad")

    resp = test_app.post(
        "/api/upload",
        headers={"X-API-Key": "testkey"},
        files={"file": ("evil.zip", evil_zip, "application/zip")},
    )
    assert resp.status_code == 400
    assert "Invalid file paths" in resp.text


def test_upload_rejects_zip_with_executable(test_app):
    evil_zip = _make_zip_with_entry("runme.exe", "binary")

    resp = test_app.post(
        "/api/upload",
        headers={"X-API-Key": "testkey"},
        files={"file": ("evil.zip", evil_zip, "application/zip")},
    )
    assert resp.status_code == 400
    assert "disallowed types" in resp.text


# =====================================================================
# R — Repudiation tests: logging
# =====================================================================

def test_download_generates_log_entry(test_app, fake_s3):
    # Arrange: make a successful download
    fake_s3["manifest"] = {"checksum": "xyz", "filename": "m2.zip"}
    fake_s3["checksum"] = "xyz"

    # Act
    resp = test_app.get("/api/download/m2.zip", headers={"X-API-Key": "testkey"})
    assert resp.status_code == 200

    # Assert: log file exists and has some content
    log_path = os.environ["LOG_FILE_PATH"]
    assert os.path.exists(log_path), "Log file was not created"

    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "download event" in content
    # If HMAC key is set, we could also assert "sig=" is present.


# =====================================================================
# I — Information Disclosure tests: no raw URLs in snippets
# =====================================================================

def test_enumerate_redacts_urls_in_card_snippet(test_app, fake_s3):
    fake_s3["models"] = [
        {"name": "m1", "key": "models/m1.zip", "size": 123, "last_modified": "2025-01-01T00:00:00Z"}
    ]
    fake_s3["card_text"] = "Data: https://private-bucket.aws/mysecretdata"

    resp = test_app.get("/api/enumerate", headers={"X-API-Key": "testkey"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1

    model = data[0]
    # Assumes your ModelMetadata includes an optional "card_snippet"
    if "card_snippet" in model:
        snippet = model["card_snippet"]
        assert "[REDACTED_URL]" in snippet
        assert "private-bucket.aws" not in snippet


# =====================================================================
# D — Denial of Service tests: rate limiting
# =====================================================================

def test_rate_limit_triggers_429(test_app):
    # We set RATE_LIMIT_PER_MIN = 3 in the fixture
    headers = {"X-API-Key": "testkey"}

    # First few calls should pass
    for i in range(3):
        r = test_app.get("/api/enumerate", headers=headers)
        assert r.status_code == 200, r.text

    # Next one should hit the limit
    r = test_app.get("/api/enumerate", headers=headers)
    assert r.status_code == 429
    assert "Rate limit exceeded" in r.text


# =====================================================================
# E — Elevation of Privilege tests: uploaded code not executable
# (We partially cover this via executable-blocking above).
# =====================================================================

def test_upload_cannot_smuggle_python_script(test_app):
    evil_zip = _make_zip_with_entry("train.py", "print('pwned')")

    resp = test_app.post(
        "/api/upload",
        headers={"X-API-Key": "testkey"},
        files={"file": ("evil.zip", evil_zip, "application/zip")},
    )
    assert resp.status_code == 400
    assert "disallowed types" in resp.text
