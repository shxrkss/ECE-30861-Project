# tests/unit/test_routes_models.py
import io
import os
import tempfile
import pytest
from fastapi.testclient import TestClient

import src.server as server
import src.services.s3_service as s3srv
from src.services.auth import verify_api_key

# override dependency to avoid dealing with keys at runtime
server.app.dependency_overrides[verify_api_key] = lambda: "unittest-user"
client = TestClient(server.app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "OK"

def test_upload_and_download_flow(monkeypatch, tmp_path):
    # create a small fake zip file
    zip_path = tmp_path / "small.zip"
    import zipfile
    with zipfile.ZipFile(str(zip_path), "w") as z:
        z.writestr("README.md", "test model card")

    # mock upload_file_to_s3 to just return True
    monkeypatch.setattr(s3srv, "upload_file_to_s3", lambda lp, key, checksum=None: True)
    # mock get_s3_object_checksum and generate_presigned_download_url
    monkeypatch.setattr(s3srv, "get_s3_object_checksum", lambda key: "deadbeef")
    monkeypatch.setattr(s3srv, "generate_presigned_download_url", lambda key, expires_in=300: "https://signed.example/download")

    with open(zip_path, "rb") as f:
        files = {"file": ("small.zip", f, "application/zip")}
        r = client.post("/api/upload", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["checksum"]  # checksum exists

    # Now request download (should return presigned URL + checksum)
    r2 = client.get("/api/download/small.zip")
    assert r2.status_code == 200
    j = r2.json()
    assert "download_url" in j and j["download_url"].startswith("https://signed.example")
    assert j["checksum"] == "deadbeef"
