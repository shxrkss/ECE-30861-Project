import re

def split_urls(line: str):
    return [u.strip() for u in line.split(",") if u.strip()]

def test_split_single():
    assert split_urls("https://a.com") == ["https://a.com"]

def test_split_commas_and_spaces():
    assert split_urls(" u1 , u2 ,, u3 ") == ["u1", "u2", "u3"]

def test_max_three_guard_value_only():
    # pure logic test: ensure our guard condition is testable
    assert len(split_urls("u1,u2,u3")) == 3
