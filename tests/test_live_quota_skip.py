"""The live suites skip when the API key's metered allowance is used up, and fail otherwise.

An exhausted allowance says nothing about whether a response model matches the server, so
it is not a contract break. Every other error still is.
"""
from __future__ import annotations

import httpx
import pytest

from mangrove_ai import MangroveAI
from mangrove_ai.exceptions import RateLimitError, ServerError
from tests.integration.quota import skip_on_exhausted_quota

pytest_plugins = ["pytester"]

#: The body the API answers once the key's monthly SIEVE allowance is spent.
QUOTA = {"detail": "limit reached: oracle_sieve_calls", "error": "quota_exceeded",
         "limit_kind": "monthly", "resource_type": "oracle_sieve_calls"}

#: A 429 that is throttling, not an exhausted allowance.
THROTTLED = {"error": "rate_limited", "message": "Too many requests", "code": "RATE_LIMITED"}


def _raised(status: int, body: dict) -> Exception:
    """The exception the real HTTP transport raises for this response."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)

    client = MangroveAI(api_key="test_abc123", environment="local", auto_retry=False,
                        httpx_client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(Exception) as info:
        client.oracle.list_datasets()
    return info.value


def test_an_exhausted_quota_skips_and_names_the_resource_and_limit() -> None:
    exc = _raised(429, QUOTA)
    with pytest.raises(pytest.skip.Exception, match="monthly oracle_sieve_calls"):
        with skip_on_exhausted_quota():
            raise exc


def test_a_429_that_is_not_a_quota_still_fails() -> None:
    exc = _raised(429, THROTTLED)
    with pytest.raises(RateLimitError):
        with skip_on_exhausted_quota():
            raise exc


def test_any_other_error_still_fails() -> None:
    exc = _raised(500, {"error": "internal_error", "message": "boom"})
    with pytest.raises(ServerError):
        with skip_on_exhausted_quota():
            raise exc


def test_the_live_suites_report_an_exhausted_quota_as_a_skip(pytester: pytest.Pytester) -> None:
    """The integration conftest applies the rule to every live test."""
    from pathlib import Path

    conftest = Path(__file__).parent / "integration" / "conftest.py"
    pytester.makeconftest(conftest.read_text())
    pytester.makepyfile(test_live=f'''
import json
from mangrove_ai.exceptions import RateLimitError

def test_quota():
    raise RateLimitError(status_code=429, error="quota_exceeded",
                         message=json.dumps({QUOTA!r}), code="UNKNOWN")

def test_throttled():
    raise RateLimitError(status_code=429, error="rate_limited",
                         message="Too many requests", code="RATE_LIMITED")
''')
    result = pytester.runpytest("-rs")
    result.assert_outcomes(skipped=1, failed=1)
    result.stdout.fnmatch_lines(["*SKIPPED*monthly oracle_sieve_calls*"])
