from __future__ import annotations

from mangroveai import MangroveAI
from mangroveai._transport._mock import MockTransport
from mangroveai.models.auth import ApiKey, ApiKeyCreateResponse, LoginResponse, RefreshResponse
from mangroveai.models.shared import SuccessResponse


def _make_client(mock: MockTransport) -> MangroveAI:
    return MangroveAI(api_key="test_abc123", environment="local", httpx_client=mock)


class TestAuthLogin:
    def test_login_returns_tokens_and_user(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/auth/login", json={
            "success": True,
            "access_token": "jwt_access_123",
            "refresh_token": "jwt_refresh_456",
            "user": {
                "id": "user-uuid-1",
                "name": "Test User",
                "email": "test@example.com",
                "org_id": "org-uuid-1",
            },
        })
        client = _make_client(mock)

        result = client.auth.login("firebase_token_abc")

        assert isinstance(result, LoginResponse)
        assert result.success is True
        assert result.access_token == "jwt_access_123"
        assert result.refresh_token == "jwt_refresh_456"
        assert result.user.id == "user-uuid-1"
        assert result.user.email == "test@example.com"

        assert len(mock.requests) == 1
        assert mock.requests[0].json == {"firebase_token": "firebase_token_abc"}


class TestAuthRefresh:
    def test_refresh_returns_new_access_token(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/auth/refresh", json={
            "success": True,
            "access_token": "new_jwt_access_789",
        })
        client = _make_client(mock)

        result = client.auth.refresh("jwt_refresh_456")

        assert isinstance(result, RefreshResponse)
        assert result.access_token == "new_jwt_access_789"
        assert mock.requests[0].json == {"refresh_token": "jwt_refresh_456"}


class TestAuthApiKeys:
    def test_list_api_keys(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/auth/api-keys", json={
            "success": True,
            "keys": [
                {
                    "id": "key-uuid-1",
                    "key_prefix": "dev_a1b2",
                    "name": "My Key",
                    "created_at": "2026-01-01T00:00:00Z",
                    "expires_at": None,
                },
            ],
        })
        client = _make_client(mock)

        result = client.auth.list_api_keys()

        assert len(result) == 1
        assert isinstance(result[0], ApiKey)
        assert result[0].id == "key-uuid-1"
        assert result[0].name == "My Key"

    def test_create_api_key(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/auth/api-keys", json={
            "success": True,
            "key": "dev_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6",
            "key_id": "key-uuid-2",
            "key_prefix": "dev_a1b2",
            "name": "New Key",
            "created_at": "2026-04-11T00:00:00Z",
            "expires_at": "2026-07-11T00:00:00Z",
        })
        client = _make_client(mock)

        result = client.auth.create_api_key("New Key", expires_days=90)

        assert isinstance(result, ApiKeyCreateResponse)
        assert result.key.startswith("dev_")
        assert result.name == "New Key"
        assert result.expires_at is not None
        assert mock.requests[0].json == {"name": "New Key", "expires_days": 90}

    def test_create_api_key_with_scopes(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/auth/api-keys", json={
            "success": True,
            "key": "dev_test",
            "key_id": "key-uuid-3",
            "key_prefix": "dev_test",
            "name": "Scoped",
            "created_at": "2026-04-11T00:00:00Z",
            "expires_at": None,
        })
        client = _make_client(mock)

        client.auth.create_api_key("Scoped", scopes=["strategy:read", "signal:read"])

        assert mock.requests[0].json == {
            "name": "Scoped",
            "scopes": ["strategy:read", "signal:read"],
        }

    def test_revoke_api_key(self) -> None:
        mock = MockTransport()
        mock.add_response("DELETE", "/auth/api-keys/key-uuid-1", json={
            "success": True,
            "message": "API key revoked",
        })
        client = _make_client(mock)

        result = client.auth.revoke_api_key("key-uuid-1")

        assert isinstance(result, SuccessResponse)
        assert result.success is True
        assert "key-uuid-1" in mock.requests[0].url
