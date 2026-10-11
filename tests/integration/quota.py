"""An exhausted metered allowance is a skip in the live suites, not a contract break."""
from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from mangrove_ai.exceptions import RateLimitError


def _limit(exc: RateLimitError) -> str:
    """The limit kind and resource the quota body names, e.g. ``monthly oracle_sieve_calls``.

    The transport keeps a body that carries no ``message`` whole as the exception's message.
    """
    try:
        body = json.loads(exc.message)
    except (TypeError, ValueError):
        body = None
    if not isinstance(body, dict):
        body = {}
    return f"{body.get('limit_kind', 'unknown')} {body.get('resource_type', 'unknown resource')}"


@contextmanager
def skip_on_exhausted_quota() -> Iterator[None]:
    """Skip the test when the API key's metered allowance is used up.

    Only a 429 whose body says ``quota_exceeded`` skips. Any other 429, and every other
    error, propagates and fails the test.
    """
    try:
        yield
    except RateLimitError as exc:
        if exc.error != "quota_exceeded":
            raise
        pytest.skip(f"the API key's {_limit(exc)} quota is used up: an exhausted allowance, "
                    f"not a contract break")
