"""Consume the same fake wire payloads used by the TypeScript client.

The contract workstream owns these shared fixture bytes. They are source-derived
HTTP boundary fixtures, not recordings of authenticated production requests.
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from mangrove_ai import AuthenticationError, MangroveAI, ServiceUnavailableError
from mangrove_ai.models import AsyncBacktestSubmission, LoginResponse, RefreshResponse

FIXTURES = Path(__file__).parents[1] / "contracts" / "mangroveai" / "fixtures"


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


def test_shared_usage_signals_and_async_status_at_http_boundary():
    seen = []

    def handler(request):
        seen.append(request)
        assert request.headers["Authorization"] == "Bearer prod_shared_fixture_not_a_real_key"
        if request.url.path == "/api/v1/users/me/metrics":
            return httpx.Response(200, json=fixture("usage-success"))
        if request.url.path == "/api/v1/signals/":
            page = "one" if request.url.params["offset"] == "0" else "two"
            return httpx.Response(200, json=fixture(f"signals-page-{page}"))
        assert request.url.path == "/api/v2/backtests/00000000-0000-4000-8000-000000000001/status"
        return httpx.Response(200, json=fixture("backtest-completed"))

    with MangroveAI(
        api_key="prod_shared_fixture_not_a_real_key", load_dotenv=False, auto_retry=False,
        httpx_client=httpx.Client(transport=httpx.MockTransport(handler)),
    ) as client:
        assert client.users.get_my_metrics().messages_count == 7
        assert [signal.name for signal in client.signals.list_iter(limit_per_page=1)] == ["fixture_one", "fixture_two"]
        assert client.backtesting.poll_status("00000000-0000-4000-8000-000000000001").status == "completed"
    assert len(seen) == 4


def test_shared_session_payloads_accept_current_absent_refresh_token():
    assert LoginResponse.model_validate(fixture("login-success")).refresh_token is None
    assert RefreshResponse.model_validate(fixture("refresh-success")).access_token == "fixture_rotated_access_token"
    assert AsyncBacktestSubmission.model_validate(fixture("backtest-submitted")).status == "running"
    assert AsyncBacktestSubmission.model_validate(fixture("backtest-running")).status == "running"


@pytest.mark.parametrize("status,name,kind", [
    (401, "unauthorized", AuthenticationError), (503, "unavailable", ServiceUnavailableError),
])
def test_shared_errors_preserve_server_decision_and_correlation(status, name, kind):
    with MangroveAI(
        api_key="prod_shared_fixture_not_a_real_key", load_dotenv=False, auto_retry=False,
        httpx_client=httpx.Client(transport=httpx.MockTransport(
            lambda request: httpx.Response(status, json=fixture(name)),
        )),
    ) as client, pytest.raises(kind) as raised:
        client.users.get_my_metrics()
    assert raised.value.status_code == status
    assert raised.value.correlation_id == "fixture-request"
