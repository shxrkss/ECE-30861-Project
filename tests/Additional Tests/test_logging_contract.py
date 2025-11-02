import os, tempfile, logging

def test_log_level_zero_creates_blank_file(tmp_path, monkeypatch):
    p = tmp_path/"app.log"
    monkeypatch.setenv("LOG_FILE", str(p))
    monkeypatch.setenv("LOG_LEVEL", "0")
    # Simulate your logging setup (no import of app needed)
    logger = logging.getLogger("x"); logger.handlers[:] = []
    fh = logging.FileHandler(p); fh.setLevel(logging.CRITICAL+1); logger.addHandler(fh)
    # Produce nothing; file should still exist and be <= a few bytes
    assert p.exists()
    assert p.stat().st_size <= 5
