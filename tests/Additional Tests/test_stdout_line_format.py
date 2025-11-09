import json

def is_valid_ndjson_line(s: str):
    try:
        obj = json.loads(s)
    except Exception:
        return False
    return isinstance(obj, dict) and "category" in obj and obj.get("category") == "MODEL"

def test_ndjson_detector():
    line = '{"category":"MODEL"}'
    assert is_valid_ndjson_line(line)
