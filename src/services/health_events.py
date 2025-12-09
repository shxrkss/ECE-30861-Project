# src/services/health_events.py
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Deque, List

@dataclass
class Event:
    timestamp: datetime
    kind: str
    user: str | None = None


# Keep only last N events in memory
_MAX_EVENTS = 5000
_events: Deque[Event] = deque(maxlen=_MAX_EVENTS)


def record_event(kind: str, user: str | None = None):
    _events.append(Event(timestamp=datetime.utcnow(), kind=kind, user=user))


def get_recent_events(minutes: int = 60) -> List[Event]:
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    return [e for e in list(_events) if e.timestamp >= cutoff]


def summarize_recent(minutes: int = 60) -> dict:
    events = get_recent_events(minutes)
    counts: dict[str, int] = {}
    for e in events:
        counts[e.kind] = counts.get(e.kind, 0) + 1
    return {
        "window_minutes": minutes,
        "total_events": len(events),
        "by_kind": counts,
    }
