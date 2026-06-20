"""WS3 (MangroveOracle#296): non-idempotent launch must not be auto-retried on a
gateway 504, and launch_experiment_and_wait confirms via polling instead."""
from __future__ import annotations

import pytest

from mangrove_ai import MangroveAI
from mangrove_ai._transport._mock import MockTransport
from mangrove_ai._transport._retry import RetryConfig
from mangrove_ai.exceptions import ServerError


def _client(mock: MockTransport) -> MangroveAI:
    return MangroveAI(api_key="test_abc123", environment="local", httpx_client=mock)


# --- RetryConfig: idempotent-only retry on transient gateway statuses ---


@pytest.mark.parametrize("status", [429, 502, 503, 504])
def test_idempotent_methods_retry(status):
    rc = RetryConfig(max_retries=3)
    for m in ("GET", "HEAD", "OPTIONS", "PUT", "DELETE"):
        assert rc.should_retry(status, 0, m) is True


@pytest.mark.parametrize("status", [429, 502, 503, 504])
def test_non_idempotent_methods_not_retried(status):
    rc = RetryConfig(max_retries=3)
    # POST/PATCH (e.g. Oracle launch) may have applied server-side → never auto-retry.
    assert rc.should_retry(status, 0, "POST") is False
    assert rc.should_retry(status, 0, "PATCH") is False


def test_non_transient_status_not_retried_even_for_get():
    rc = RetryConfig(max_retries=3)
    assert rc.should_retry(500, 0, "GET") is False
    assert rc.should_retry(400, 0, "GET") is False


def test_default_method_is_idempotent():
    # Back-compat: callers that don't pass a method get GET semantics.
    assert RetryConfig().should_retry(504, 0) is True


# --- launch_experiment_and_wait: 504 → poll, don't re-launch ---

def test_launch_and_wait_polls_on_504(monkeypatch):
    client = _client(MockTransport())
    calls = {"launch": 0, "get": 0}

    def fake_launch(experiment_id):
        calls["launch"] += 1
        raise ServerError(504, "upstream_timeout", "gateway timeout", "GATEWAY_TIMEOUT")

    def fake_get(experiment_id):
        calls["get"] += 1
        # First poll: still validated; second: advanced to preparing.
        return {"status": "validated"} if calls["get"] < 2 else {"status": "preparing", "experiment_id": experiment_id}

    monkeypatch.setattr(client.oracle, "launch_experiment", fake_launch)
    monkeypatch.setattr(client.oracle, "get_experiment", fake_get)

    result = client.oracle.launch_experiment_and_wait("exp1", poll_interval=0, timeout=10)
    assert result["status"] == "preparing"
    assert calls["launch"] == 1          # launched exactly once — never re-POSTed
    assert calls["get"] >= 2


def test_launch_and_wait_reraises_non_gateway_error(monkeypatch):
    client = _client(MockTransport())

    def fake_launch(experiment_id):
        raise ServerError(400, "bad_request", "nope", "BAD")

    monkeypatch.setattr(client.oracle, "launch_experiment", fake_launch)
    with pytest.raises(ServerError):
        client.oracle.launch_experiment_and_wait("exp1", poll_interval=0, timeout=1)
