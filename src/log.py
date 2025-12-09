import logging
import re
from logging.handlers import RotatingFileHandler
import os
import hmac
import hashlib

LOG_FILE = os.getenv("LOG_FILE_PATH", "logs/app.log")
os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)

REDACT_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED_AWS_KEY]"),
    (re.compile(r"(?i)api[_-]?key[:=]\s*[A-Za-z0-9\-_]+"), "API_KEY=[REDACTED]"),
    (re.compile(r"(?i)github[_-]?token[:=]\s*[A-Za-z0-9\-_]+"), "GITHUB_TOKEN=[REDACTED]"),
]

# Optional key for signing logs
HMAC_KEY = os.getenv("LOG_HMAC_KEY", "")

class RedactingFormatter(logging.Formatter):
    def format(self, record):
        msg = super().format(record)

        # redact secrets
        for pat, repl in REDACT_PATTERNS:
            msg = pat.sub(repl, msg)

        # flatten newlines
        msg = msg.replace("\n", " ").replace("\r", " ")

        # attach HMAC signature if configured
        if HMAC_KEY:
            sig = hmac.new(HMAC_KEY.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
            msg = f"{msg} | sig={sig}"

        return msg

def setup_logging(level=logging.INFO):
    root = logging.getLogger()
    root.setLevel(level)

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(RedactingFormatter("[%(asctime)s] %(levelname)s %(name)s - %(message)s"))

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(RedactingFormatter("%(levelname)s: %(message)s"))

    # Reset any old handlers
    if root.handlers:
        for h in list(root.handlers):
            root.removeHandler(h)

    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    # quiet noisy libs
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger("trustworthy-registry")
