import sys
import json
import asyncio
from pathlib import Path

# This file is used to run tests on the phase 1 portion of the project to ensure that 
# we have a fully functioning phase 1 foundation so that it doesn't cause issues down 
# the line.

try: 
    from src.metrics import run_metrics, Urlcategory
except Exception:
    from src.metrics import run_metrics, UrlCategory
    
def classify_url(raw:str):
    s = raw.strip()
    if "huggingface.co" in s:
        if "/datasets/" in s or s.rstrip("/").endswith("/datasets"):
            return UrlCategory.DATASET, {"url": s}
        return UrlCategory.MODEL, {"url": s}
    if "github.com" in s:
        return UrlCategory.CODE, {"url": s}
    return None, {"url": s}

def grade_line(line: str) -> dict:
    url_map = {}
    for u in [x.strip() for x in line.split(",") if x.strip()]:
        cat, ids = classify_url(u)
        if cat is not None:
            url_map[cat] = ids
    
    return asyncio.run(run_metrics(url_map))

def main():
    if len(sys.argv) != 2:
        print("Usage: phase1_cli.py <URL_FILE or '-'>", file=sys.stderr); sys.exit(2)

    source = sys.argv[1]
    lines = sys.stdin.read().splitlines() if source == "-" else Path(source).read_text(encoding="utf-8").splitlines()
    for ln in lines:
        ln = ln.strip()
        if not ln: 
            continue
        # IMPORTANT: one NDJSON line per MODEL
        out = grade_line(ln)
        print(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()