import importlib
import types
import pytest

def make_fake_s3_client(head_obj=None, presigned_url="https://example.com/get", list_pages=None):
    class FakeClient:
        def __init__(self):
            self._head = head_obj or {}
            self._presigned = presigned_url
            self._pages = list_pages or []

        def head_object(self, Bucket, Key):
            if "NoSuchKey" in Key:
                from botocore.exceptions import ClientError
                raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
            return self._head

        def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):
            return self._presigned

        def get_paginator(self, name):
            class Paginator:
                def paginate(inner_self, Bucket, Prefix):
                    # return list of pages as dicts
                    for p in self._pages:
                        yield p
            return Paginator()

    return FakeClient()

def reload_s3_with_fake_client(monkeypatch, fake_client):
    # reload module after patching s3_client
    import src.services.s3_service as s3srv
    importlib.reload(s3srv)
    monkeypatch.setattr(s3srv, "s3_client", fake_client)
    return s3srv

def test_get_s3_object_checksum_metadata(monkeypatch):
    fake_head = {"Metadata": {"checksum": "abc123"}, "ETag": '"etagvalue"'}
    fake = make_fake_s3_client(head_obj=fake_head)
    import src.services.s3_service as s3srv
    # set s3_client to fake
    monkeypatch.setattr(s3srv, "s3_client", fake)
    assert s3srv.get_s3_object_checksum("models/exists.zip") == "abc123"

def test_get_s3_object_checksum_etag_fallback(monkeypatch):
    fake_head = {"Metadata": {}, "ETag": '"etagvalue"'}
    fake = make_fake_s3_client(head_obj=fake_head)
    import src.services.s3_service as s3srv
    monkeypatch.setattr(s3srv, "s3_client", fake)
    assert s3srv.get_s3_object_checksum("models/withetag.zip") == "etagvalue"

def test_generate_presigned_download_url(monkeypatch):
    fake = make_fake_s3_client(presigned_url="https://download/test")
    import src.services.s3_service as s3srv
    monkeypatch.setattr(s3srv, "s3_client", fake)
    url = s3srv.generate_presigned_download_url("models/x.zip")
    assert url == "https://download/test"

def test_list_s3_models(monkeypatch):
    pages = [
        {"Contents": [{"Key": "models/a.zip", "Size": 100, "LastModified": "2025-01-01T00:00:00Z"},
                      {"Key": "models/b.txt", "Size": 10, "LastModified": "2025-01-02T00:00:00Z"}]},
        {"Contents": [{"Key": "models/sub/c.zip", "Size": 200, "LastModified": "2025-01-03T00:00:00Z"}]}
    ]
    fake = make_fake_s3_client(list_pages=pages)
    import src.services.s3_service as s3srv
    monkeypatch.setattr(s3srv, "s3_client", fake)
    res = s3srv.list_s3_models("models/")
    # Should include only .zip files
    names = [m["name"] for m in res]
    assert "a" in names
    assert "c" in names
    assert not any(m["name"].endswith(".txt") for m in res)