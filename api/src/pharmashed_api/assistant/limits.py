"""Usage limits for the assistant endpoint.

The assistant spends a paid/quota'd model key, and the public demo has no login, so two
in-memory limits protect it: a per-client limit per hour, and a global limit per day.
State lives in this process (fine for a single free-tier instance; it resets on restart).

Limits come from the environment on every call so they can be tuned without a deploy:
ASSISTANT_IP_LIMIT (default 20 questions per client per hour) and
ASSISTANT_DAILY_LIMIT (default 800 questions per UTC day, all clients).
Set either to 0 to disable that limit.
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

_HOUR = 3600.0


class UsageLimiter:
    """Sliding-window per-client limit plus a per-UTC-day global counter."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_client: dict[str, deque[float]] = defaultdict(deque)
        self._day = ""
        self._day_count = 0

    def reset(self) -> None:
        with self._lock:
            self._by_client.clear()
            self._day = ""
            self._day_count = 0

    def check(self, client: str, now: float | None = None) -> str | None:
        """Record a question from `client` if allowed; otherwise return why it was refused."""
        now = time.time() if now is None else now
        per_client = int(os.environ.get("ASSISTANT_IP_LIMIT", "20"))
        per_day = int(os.environ.get("ASSISTANT_DAILY_LIMIT", "800"))
        today = datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%d")

        with self._lock:
            if today != self._day:
                self._day, self._day_count = today, 0
            if per_day and self._day_count >= per_day:
                return "The assistant has reached its daily limit for this demo. Please try again tomorrow."

            window = self._by_client[client]
            while window and now - window[0] > _HOUR:
                window.popleft()
            if per_client and len(window) >= per_client:
                return "You have asked a lot of questions in the last hour. Please wait a little and try again."

            window.append(now)
            self._day_count += 1
            return None


limiter = UsageLimiter()
