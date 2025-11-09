#!/usr/bin/env python3
"""
Phase-1 probe: discover and run src/metrics/*_metric.py and emit one NDJSON line per input.

Supports:
- Module-level metrics:  compute / score / evaluate / run / get_score
- Class-based metrics :  <AnyClass>.compute / score / evaluate / run / get_score
  (constructor may require `name` -> we try: (), (name), (name=<stem>))

Extras:
- If a callable declares an `allowed` parameter (e.g., license checks), we pass a list of SPDX IDs.
  Uses module-level ALLOWED if present, else a permissive default.
- If a callable declares an *_id param (id, model_id, repo_id, dataset_id, hf_id), we pass an HF repo id
  derived from the input URL (org/name).
- Per-metric timeout (5s) so a hang won't block output.
- Robust: errors/timeouts -> score 0 (latency 0). Always prints exactly one NDJSON line.

Usage:
  echo 'https://huggingface.co/facebook/opt-125m' | python3 phase1_probe.py -
  python3 phase1_probe.py urls.txt
  python3 phase1_probe.py --debug urls.txt
"""
from __future__ import annotations
import sys, json, asyncio, pathlib, time, inspect, traceback, re
import importlib.util as iutil
from typing import Any, Dict, Tuple, Iterable, Optional

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "src"
METRICS_DIR = SRC / "metrics"
NETSCORE_PATH = SRC / "netscore.py"

METRIC_TIMEOUT_SEC = 5
DEBUG = ("--debug" in sys.argv)

# filename (without .py) -> NDJSON field (None means skip for Phase-1 output)
KEYMAP: Dict[str, str | None] = {
    "bus_metric": "bus_factor",
    "code_quality_metric": "code_quality",
    "dataset_code_score_metric": "dataset_and_code_score",
    "dataset_quality_metric": "dataset_quality",
    "license_metric": "license",
    "performance_metric": "performance_claims",
    "ramp_metric": "ramp_up_time",
    "size_metric": "size_score",
    # non Phase-1 fields:
    "reproducibility_metric": None,
    "reviewedness_metric": None,
    # test files:
    "test_bus_metric": None,
    "test_size_metric": None,
}

FN_CANDIDATES = ("compute", "score", "evaluate", "run", "get_score")

DEFAULT_ALLOWED: tuple[str, ...] = (
    "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause",
    "MPL-2.0", "CC-BY-4.0",
)

_HF_REPO_RE = re.compile(r"https?://huggingface\.co/([^/\s]+)/([^/\s]+)")

def log(*a: Any) -> None:
    if DEBUG:
        print("[probe]", *a, file=sys.stderr, flush=True)

def clamp01(x: Any) -> float:
    try:
        x = float(x)
    except Exception:
        return 0.0
    return 0.0 if x < 0 else (1.0 if x > 1 else x)

def classify_url(raw: str) -> Tuple[str, Dict[str, str]]:
    s = raw.strip()
    if "huggingface.co" in s:
        if "/datasets/" in s or s.rstrip("/").endswith("/datasets"):
            return "DATASET", {"url": s}
        return "MODEL", {"url": s}
    if "github.com" in s:
        return "CODE", {"url": s}
    return "OTHER", {"url": s}

def extract_hf_id(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    m = _HF_REPO_RE.match(url.strip())
    if not m:
        return None
    org, name = m.group(1), m.group(2)
    return f"{org}/{name}"

def _allowed_from_module(mod) -> Iterable[str]:
    allowed = getattr(mod, "ALLOWED", None)
    if allowed is None:
        return DEFAULT_ALLOWED
    try:
        return tuple(str(x) for x in allowed)
    except Exception:
        return DEFAULT_ALLOWED

def load_mod(path: pathlib.Path):
    name = f"_probe_{path.stem}_{abs(hash(str(path)))%1_000_000}"
    spec = iutil.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        log("no spec for", path)
        return None
    mod = iutil.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
        log("loaded", path)
        return mod
    except Exception as e:
        log("import failed", path, "->", repr(e))
        log(traceback.format_exc())
        return None

async def _call_normalized(fn, mod, model_url, code_url, dataset_url):
    """
    Call fn using friendly signatures; inject kwargs if requested by signature:
      - allowed=...
      - *_id (id, model_id, repo_id, dataset_id, hf_id) with extracted HF repo id
    Normalize to (score, latency_ms).
    """
    try:
        sig = inspect.signature(fn)
    except Exception:
        sig = None

    wants_allowed = False
    id_param: Optional[str] = None
    kwargs = {}

    if sig is not None:
        for n, p in sig.parameters.items():
            if p.kind not in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY):
                continue
            if n == "allowed":
                wants_allowed = True
            elif n in ("id", "model_id", "repo_id", "dataset_id", "hf_id"):
                id_param = n

    if wants_allowed:
        kwargs["allowed"] = _allowed_from_module(mod)

    if id_param:
        hf_id = extract_hf_id(code_url) or extract_hf_id(model_url) or extract_hf_id(dataset_url)
        if hf_id:
            kwargs[id_param] = hf_id

    t0 = time.perf_counter_ns()

    # Try kwargs-only first (covers pure keyword APIs)
    if kwargs:
        try:
            res = fn(**kwargs)
            if asyncio.iscoroutine(res):
                res = await res
            if isinstance(res, tuple) and len(res) == 2:
                score, lat = res
                return score, int(lat)
            lat_ms = int((time.perf_counter_ns() - t0) / 1_000_000)
            return res, lat_ms
        except TypeError:
            pass
        except Exception:
            pass

    # Then positional forms:
    try:
        res = fn(model_url, code_url, dataset_url, **kwargs)
    except TypeError:
        try:
            best = code_url or model_url or dataset_url
            res = fn(best, **kwargs)
        except TypeError:
            try:
                res = fn({"MODEL": model_url, "CODE": code_url, "DATASET": dataset_url}, **kwargs)
            except TypeError:
                res = fn(**kwargs)

    if asyncio.iscoroutine(res):
        res = await res

    if isinstance(res, tuple) and len(res) == 2:
        score, lat = res
        return score, int(lat)
    lat_ms = int((time.perf_counter_ns() - t0) / 1_000_000)
    return res, lat_ms

async def call_metric(mod, metric_name: str, model_url: Optional[str], code_url: Optional[str], dataset_url: Optional[str]):
    # Module-level functions
    for name in FN_CANDIDATES:
        fn = getattr(mod, name, None)
        if callable(fn):
            try:
                return await asyncio.wait_for(
                    _call_normalized(fn, mod, model_url, code_url, dataset_url),
                    timeout=METRIC_TIMEOUT_SEC,
                )
            except asyncio.TimeoutError:
                log(mod.__name__, f"{name} timed out")
                return 0.0, 0
            except Exception as e:
                log(mod.__name__, f"{name} raised:", repr(e))
                log(traceback.format_exc())
                return 0.0, 0

    # Class-based metrics
    for obj_name, obj in mod.__dict__.items():
        if not inspect.isclass(obj):
            continue
        if obj_name.lower().endswith("base"):
            continue
        method_name = next((m for m in FN_CANDIDATES if callable(getattr(obj, m, None))), None)
        if not method_name:
            continue

        inst = None
        # Try constructors: (), (name), (name=metric_name) — catch ANY exception
        try:
            inst = obj()
        except Exception:
            try:
                inst = obj(metric_name)
            except Exception:
                try:
                    inst = obj(name=metric_name)
                except Exception as e:
                    log(mod.__name__, f"{obj_name} ctor failed:", repr(e))
                    continue  # next class

        try:
            fn = getattr(inst, method_name)
            return await asyncio.wait_for(
                _call_normalized(fn, mod, model_url, code_url, dataset_url),
                timeout=METRIC_TIMEOUT_SEC,
            )
        except asyncio.TimeoutError:
            log(mod.__name__, f"class.{method_name} timed out")
            return 0.0, 0
        except Exception as e:
            log(mod.__name__, f"class.{method_name} raised:", repr(e))
            log(traceback.format_exc())
            return 0.0, 0

    log(mod.__name__, "no callable metric found")
    return 0.0, 0

def empty_ndjson() -> Dict[str, Any]:
    return {
        "name": "",
        "category": "MODEL",
        "net_score": 0.0, "net_score_latency": 0,
        "ramp_up_time": 0.0, "ramp_up_time_latency": 0,
        "bus_factor": 0.0, "bus_factor_latency": 0,
        "performance_claims": 0.0, "performance_claims_latency": 0,
        "license": 0.0, "license_latency": 0,
        "size_score": {"raspberry_pi": 0.0, "jetson_nano": 0.0, "desktop_pc": 0.0, "aws_server": 0.0},
        "size_score_latency": 0,
        "dataset_and_code_score": 0.0, "dataset_and_code_score_latency": 0,
        "dataset_quality": 0.0, "dataset_quality_latency": 0,
        "code_quality": 0.0, "code_quality_latency": 0,
    }

async def grade_line(line: str) -> Dict[str, Any]:
    log("grade_line:", line)
    # Parse URLs (support comma-separated model,code,dataset)
    url_map: Dict[str, Dict[str, str]] = {}
    for u in [x.strip() for x in line.split(",") if x.strip()]:
        cat, ids = classify_url(u)
        url_map[cat] = ids

    model_url   = (url_map.get("MODEL")   or {}).get("url")
    dataset_url = (url_map.get("DATASET") or {}).get("url")
    code_url    = (url_map.get("CODE")    or {}).get("url")

    out = empty_ndjson()

    files = sorted(METRICS_DIR.glob("*_metric.py"))
    log("metrics:", [p.name for p in files])

    for p in files:
        stem = p.stem
        key = KEYMAP.get(stem)
        if key is None:
            log("skip(non-phase1):", p.name)
            continue

        mod = load_mod(p)
        if not mod:
            continue

        score, lat = await call_metric(mod, stem, model_url, code_url, dataset_url)

        if key == "size_score":
            out["size_score_latency"] = int(lat)
            if isinstance(score, dict):
                for k in out["size_score"]:
                    out["size_score"][k] = clamp01(score.get(k, 0.0))
            else:
                for k in out["size_score"]:
                    out["size_score"][k] = clamp01(score)
        elif key in out:
            out[key] = clamp01(score)
            out[f"{key}_latency"] = int(lat)
        else:
            log("ignored key from", p.name, "->", key)

    # Optional: netscore if present (expects compute(out) -> (net, latency))
    if NETSCORE_PATH.exists():
        ns_mod = load_mod(NETSCORE_PATH)
        if ns_mod and hasattr(ns_mod, "compute"):
            try:
                net, nlat = ns_mod.compute(out)  # type: ignore[attr-defined]
                out["net_score"] = clamp01(net)
                out["net_score_latency"] = int(nlat)
            except Exception as e:
                log("netscore failed:", repr(e))
                log(traceback.format_exc())

    return out

def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--debug"]
    if len(args) != 1:
        print("Usage: phase1_probe.py [--debug] <URL_FILE or '-'>", file=sys.stderr)
        return 2

    src = args[0]
    log("ROOT:", ROOT); log("SRC:", SRC); log("METRICS_DIR exists:", METRICS_DIR.exists())

    try:
        lines = (sys.stdin.read().splitlines() if src == "-"
                 else pathlib.Path(src).read_text(encoding="utf-8").splitlines())
    except Exception as e:
        log("failed to read input:", repr(e))
        lines = []

    if not lines:
        lines = ["https://huggingface.co/facebook/opt-125m"]  # public, non-gated

    log("num lines:", len(lines))

    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            result = asyncio.run(grade_line(ln))
        except Exception as e:
            log("grade_line crashed:", repr(e))
            log(traceback.format_exc())
            result = empty_ndjson()
        print(json.dumps(result, ensure_ascii=False), flush=True)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
