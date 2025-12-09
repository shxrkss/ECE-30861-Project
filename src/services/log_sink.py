# src/services/log_sink.py
import os
import time
import tempfile
from datetime import datetime

# These env vars are optional – if not set, sink does nothing
LOG_SINK_BUCKET = os.getenv("AWS_LOG_BUCKET", "")
LOG_SINK_PREFIX = os.getenv("AWS_LOG_PREFIX", "app-logs/")

def mirror_log_line_to_s3(line: str) -> bool:
    """
    Optional: mirror a single log line to S3.
    This function is NOT wired into logging by default.
    It imports S3 lazily to avoid startup failures.
    """
    if not LOG_SINK_BUCKET:
        return False

    # Lazy import to avoid circular deps / startup issues
    try:
        from src.services.s3_service import upload_file_to_s3
    except Exception:
        return False

    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    tmp = tempfile.NamedTemporaryFile(delete=False)
    try:
        tmp.write(line.encode("utf-8"))
        tmp.flush()
        tmp.close()
        key = f"{LOG_SINK_PREFIX}{ts}.log"
        upload_file_to_s3(tmp.name, key)
        os.unlink(tmp.name)
        return True
    except Exception:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        return False
