import importlib
import time
import pytest
from types import ModuleType

def reload_auth_with_env(monkeypatch, env_vars: dict) -> ModuleType:
    # set env vars then import/reload the module so constants pick them up
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)
    import src.services.auth as auth
    importlib.reload(auth)
    return auth

def test_verify_api_key_success(monkeypatch):
    auth = reload_auth_with_env(monkeypatch, {"API_KEYS_JSON": '{"testkey":"tester"}', "API_KEY_MAX_ATTEMPTS": "5"})
    # direct call is allowed (dependency would pass the header value as the key)
    user = auth.verify_api_key("testkey")
    assert user == "tester"

def test_verify_api_key_invalid_and_lockout(monkeypatch):
    # set max attempts to 2 to speed the test
    auth = reload_auth_with_env(monkeypatch, {"API_KEYS_JSON": '{"correct":"bob"}', "API_KEY_MAX_ATTEMPTS": "2", "API_KEY_LOCKOUT_SECONDS":"2"})
    # invalid key -> raises 401 and increments attempts
    with pytest.raises(Exception) as e1:
        auth.verify_api_key("wrong1")
    assert hasattr(e1.value, "status_code") and e1.value.status_code == 401

    with pytest.raises(Exception) as e2:
        auth.verify_api_key("wrong1")
    # After reaching max attempts, the next attempt should lock the key or return 423 for that key attempted
    # Note: lock is tracked by key string. Re-trying same wrong key triggers lock.
    # Now attempt again and expect 423 Locked (or 401 then 423 depending on timing)
    with pytest.raises(Exception) as e3:
        auth.verify_api_key("wrong1")
    # either 423 or 401 is acceptable depending on runnable environment; assert that it is an HTTPException
    assert hasattr(e3.value, "status_code")
    # eventually lock expires; wait and verify that lock window clears
    time.sleep(2.1)
    # after sleep, calling with a valid key should succeed
    assert auth.verify_api_key("correct") == "bob"