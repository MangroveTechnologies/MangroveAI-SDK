from __future__ import annotations

import logging
import random
import time

logger = logging.getLogger(__name__)

# HTTP methods that are idempotent by spec — re-sending them is safe. POST and
# PATCH are NOT here: a gateway 429/5xx on a non-idempotent request may have
# ALREADY been applied server-side, so auto-retrying can double-apply (e.g. an
# Oracle sweep launch that 504s at the gateway but succeeded → a retry then hits
# the single-flight 409 / concurrent-cap 429 / double charge). Non-idempotent
# callers confirm via a follow-up read instead (see
# OracleService.launch_experiment / launch_experiment_and_wait).
_IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})


class RetryConfig:
    """Configuration for retry behavior on transient failures."""

    def __init__(self, max_retries: int = 3, auto_retry: bool = True) -> None:
        self.max_retries = max_retries
        self.auto_retry = auto_retry

    def should_retry(self, status_code: int, attempt: int, method: str = "GET") -> bool:
        if not self.auto_retry or attempt >= self.max_retries:
            return False
        if status_code not in (429, 502, 503, 504):
            return False
        # Only auto-retry idempotent methods on a transient gateway status.
        return method.upper() in _IDEMPOTENT_METHODS

    def wait_time(self, attempt: int, retry_after: int | None = None) -> float:
        if retry_after is not None:
            return float(retry_after)
        base = min(2 ** attempt, 30)
        jitter = random.uniform(0, base * 0.5)
        return base + jitter

    def wait(self, attempt: int, retry_after: int | None = None) -> None:
        wait = self.wait_time(attempt, retry_after)
        logger.debug("Retrying in %.1fs (attempt %d/%d)", wait, attempt + 1, self.max_retries)
        time.sleep(wait)
