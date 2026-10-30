"""Exercise real SDK/httpx behavior at an intercepted HTTP boundary."""
from __future__ import annotations

import json

import httpx
import pytest

from mangrove_ai import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    MalformedResponseError,
    MangroveAI,
    PaymentRequiredError,
    RateLimitError,
    ServiceUnavailableError,
)

FAKE_KEY = "prod_audit_fixture_not_a_real_key"
USER = {"id": "u1", "org_id": "o1", "name": "Fixture", "email": "fixture@example.invalid"}


def client_for(handler, **options):
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return MangroveAI(api_key=FAKE_KEY, load_dotenv=False, auto_retry=False, httpx_client=http, **options)


def test_usage_uses_bearer_and_preserves_configured_http_timeouts():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"success": True, "metrics": {"messages_count": 7}})

    with client_for(handler, timeout=2.5) as client:
        assert client.users.get_my_metrics().messages_count == 7
    assert seen[0].headers["Authorization"] == f"Bearer {FAKE_KEY}"
    assert seen[0].url.path == "/api/v1/users/me/metrics"
    assert seen[0].extensions["timeout"] == dict.fromkeys(("connect", "read", "write", "pool"), 2.5)


def test_explicit_transport_timeout_overrides_the_default():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={})

    with client_for(handler, timeout=2.5) as client:
        client._core_transport.request("GET", "/fixture", timeout=1.0)
    assert seen[0].extensions["timeout"]["read"] == 1.0


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True])
def test_invalid_timeout_fails_before_http(timeout):
    with pytest.raises(ConfigurationError, match="finite positive"):
        MangroveAI(api_key=FAKE_KEY, load_dotenv=False, timeout=timeout)


@pytest.mark.parametrize("status,error_class", [
    (401, AuthenticationError), (402, PaymentRequiredError), (403, AuthorizationError),
    (429, RateLimitError), (503, ServiceUnavailableError),
])
def test_structured_errors_keep_status_and_retry_but_redact_reflected_credentials(status, error_class):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(status, json={
            "error": "fixture_error", "message": f"Rejected Bearer {FAKE_KEY}",
            "code": "FIXTURE_ERROR", "correlation_id": "fixture-correlation",
        }, headers={"Retry-After": "7"})

    with client_for(handler) as client, pytest.raises(error_class) as raised:
        client.users.get_my_metrics()
    assert raised.value.status_code == status
    assert raised.value.retry_after == 7
    assert raised.value.correlation_id == "fixture-correlation"
    assert FAKE_KEY not in str(raised.value)
    assert len(requests) == 1


@pytest.mark.parametrize("payload", [{"success": False, "metrics": {}}, {"success": True}, []])
def test_usage_does_not_turn_a_malformed_success_into_empty_metrics(payload):
    with client_for(lambda request: httpx.Response(200, json=payload)) as client:
        with pytest.raises(MalformedResponseError):
            client.users.get_my_metrics()


def test_html_success_raises_a_contract_error_without_echoing_the_body():
    with client_for(lambda request: httpx.Response(200, text=f"<html>{FAKE_KEY}</html>")) as client:
        with pytest.raises(MalformedResponseError) as raised:
            client.users.get_my_metrics()
    assert FAKE_KEY not in str(raised.value)


def test_redirect_does_not_forward_the_credential_or_parse_as_success():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(307, headers={"Location": "https://other.example.invalid/collect"})

    with client_for(handler) as client, pytest.raises(APIError) as raised:
        client.users.get_my_metrics()
    assert raised.value.status_code == 307
    assert len(seen) == 1


def session_handler(requests, *, refresh_status=200):
    def handler(request):
        requests.append(request)
        if request.url.path == "/api/v1/auth/login":
            assert json.loads(request.content) == {"firebase_token": "fake-firebase-token"}
            return httpx.Response(200, json={
                "success": True, "access_token": "session-old", "refresh_token": None, "user": USER,
            }, headers=[
                ("Set-Cookie", "mg_refresh=fake-refresh-cookie; HttpOnly; Secure; Path=/api/v1/auth"),
                ("Set-Cookie", "mg_csrf=fake-csrf-cookie; Secure; Path=/api/v1/auth"),
            ])
        if request.url.path == "/api/v1/auth/refresh":
            assert request.headers["X-CSRF-Token"] == "fake-csrf-cookie"
            assert "mg_refresh=fake-refresh-cookie" in request.headers["Cookie"]
            assert request.content == b""
            return httpx.Response(refresh_status, json={
                "success": refresh_status == 200, "access_token": "session-new",
                "error": "session_error", "message": "Session unavailable", "code": "SESSION_ERROR",
            })
        if request.headers.get("Authorization") != "Bearer session-new":
            return httpx.Response(401, json={"error": "Unauthorized", "message": "Expired", "code": "EXPIRED"})
        return httpx.Response(200, json={"success": True, "metrics": {"messages_count": 9}})
    return handler


def test_session_refresh_uses_cookie_and_csrf_then_retries_once_for_v1_and_v2():
    seen = []
    with client_for(session_handler(seen)) as client:
        assert client.auth.login("fake-firebase-token").refresh_token is None
        # A v2 failure refreshes through v1 and updates both transports.
        client._core_v2_transport.request("GET", "/agent/conversations")
        assert client.users.get_my_metrics().messages_count == 9
    assert [request.url.path for request in seen] == [
        "/api/v1/auth/login", "/api/v2/agent/conversations", "/api/v1/auth/refresh",
        "/api/v2/agent/conversations", "/api/v1/users/me/metrics",
    ]
    assert seen[-1].headers["Authorization"] == "Bearer session-new"
    assert "Cookie" not in seen[-1].headers  # Auth cookies remain scoped to auth routes.


def test_auto_auth_false_leaves_expired_session_for_the_caller():
    seen = []
    with client_for(session_handler(seen), auto_auth=False) as client:
        client.auth.login("fake-firebase-token")
        with pytest.raises(AuthenticationError):
            client.users.get_my_metrics()
    assert len(seen) == 2


def test_failed_refresh_does_not_recurse_or_retry_the_original_request():
    seen = []
    with client_for(session_handler(seen, refresh_status=401)) as client:
        client.auth.login("fake-firebase-token")
        with pytest.raises(AuthenticationError):
            client.users.get_my_metrics()
    assert [request.url.path for request in seen].count("/api/v1/auth/refresh") == 1
    assert len(seen) == 3


def test_cookie_scope_does_not_supply_csrf_to_another_origin():
    seen = []
    with client_for(session_handler(seen)) as client:
        client.auth.login("fake-firebase-token")
        client.configure_service("core", "https://other.example.invalid/api/v1")
        with pytest.raises(ConfigurationError, match="CSRF cookie"):
            client.auth.refresh()
    assert len(seen) == 1
