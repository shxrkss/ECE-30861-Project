# src/services/rate_limit.py
import os
import time
from typing import Optional
from fastapi import Depends, HTTPException
from src.services.auth import verify_api_key
try:
    import redis
except Exception:
    redis = None

REDIS_URL = os.getenv("REDIS_URL", "")
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", 60))

# Fallback in-memory store
_in_memory = {}

def _now_minute() -> int:
    return int(time.time() // 60)

class RateLimiter:
    def __init__(self):
        self.use_redis = bool(REDIS_URL) and redis is not None
        if self.use_redis:
            self.client = redis.from_url(REDIS_URL)
        else:
            self.client = None

    def allow(self, key: str, limit: int = RATE_LIMIT_PER_MIN) -> bool:
        if self.use_redis:
            # incr and set expiry to 61 seconds
            p = f"rl:{key}:{_now_minute()}"
            try:
                val = self.client.incr(p)
                if val == 1:
                    self.client.expire(p, 61)
                return val <= limit
            except Exception:
                # on redis error fallback to in-memory
                return self._allow_in_memory(key, limit)
        else:
            return self._allow_in_memory(key, limit)

    def _allow_in_memory(self, key: str, limit: int) -> bool:
        minute = _now_minute()
        cnt, ts = _in_memory.get(key, (0, minute))
        if ts != minute:
            cnt = 1
            ts = minute
        else:
            cnt += 1
        _in_memory[key] = (cnt, ts)
        return cnt <= limit

rate_limiter = RateLimiter()



def enforce_rate_limit(user_info: dict = Depends(verify_api_key)):
    """Apply rate limit AFTER authentication."""
    user_id = user_info.get("user", "unknown")
    if not rate_limiter.allow(user_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    return user_info  # pass user info forward

def reset_rate_limit_state():
    """
    Clear in-memory rate limiter state. Redis-based limits will expire naturally.
    """
    _in_memory.clear()