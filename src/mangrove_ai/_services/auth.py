from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .._transport._service import ServiceTransport
from ..exceptions import ConfigurationError, MalformedResponseError
from ..models.auth import ApiKey, ApiKeyCreateResponse, LoginResponse, RefreshResponse
from ..models.shared import SuccessResponse
from ._base import BaseService


class AuthService(BaseService):
    """Authentication and API key management."""

    def __init__(self, transport: ServiceTransport, on_session: Callable[[str], None] | None = None) -> None:
        super().__init__(transport)
        self._on_session = on_session

    def login(self, firebase_token: str) -> LoginResponse:
        """Exchange a Firebase ID token for MangroveAI JWT tokens.

        Args:
            firebase_token: Firebase ID token from Google OAuth.

        Returns:
            Access token and user info. Current refresh tokens stay in the
            same client's httpOnly cookie jar, not the response body.
        """
        data = self._request("POST", "/auth/login", json={"firebase_token": firebase_token})
        response = LoginResponse.model_validate(data)
        if not response.success:
            raise MalformedResponseError("Login did not return a successful session.")
        if self._on_session is not None:
            self._on_session(response.access_token)
        return response

    def refresh(self, refresh_token: str | None = None) -> RefreshResponse:
        """Refresh an expired access token.

        Args:
            refresh_token: Retained for a clear compatibility error. The
                current API accepts only the cookie from this client's login.

        Returns:
            RefreshResponse with a new access_token.
        """
        if refresh_token is not None:
            raise ConfigurationError(
                "Body refresh tokens are no longer supported. Log in with this client, then call auth.refresh()."
            )
        csrf = self._transport.get_csrf_token("/auth/refresh")
        if not csrf:
            raise ConfigurationError(
                "No session CSRF cookie is available. Log in with this same client before refreshing."
            )
        data = self._transport.request("POST", "/auth/refresh", headers={"X-CSRF-Token": csrf}).json()
        response = RefreshResponse.model_validate(data)
        if not response.success:
            raise MalformedResponseError("Refresh did not return a successful session.")
        if self._on_session is not None:
            self._on_session(response.access_token)
        return response

    def list_api_keys(self) -> list[ApiKey]:
        """List all API keys for the authenticated user (masked)."""
        return self._request_list("GET", "/auth/api-keys", ApiKey, key="keys")

    def create_api_key(
        self,
        name: str,
        scopes: list[str] | None = None,
        expires_days: int | None = None,
    ) -> ApiKeyCreateResponse:
        """Generate a new API key.

        Args:
            name: Human-readable name for the key.
            scopes: Optional list of permission scopes.
            expires_days: Optional expiration in days.

        Returns:
            ApiKeyCreateResponse containing the full key (shown only once).
        """
        body: dict[str, Any] = {"name": name}
        if scopes is not None:
            body["scopes"] = scopes
        if expires_days is not None:
            body["expires_days"] = expires_days

        data = self._request("POST", "/auth/api-keys", json=body)
        return ApiKeyCreateResponse.model_validate(data)

    def revoke_api_key(self, key_id: str) -> SuccessResponse:
        """Revoke an API key by ID.

        Args:
            key_id: UUID of the key to revoke.
        """
        data = self._request("DELETE", f"/auth/api-keys/{key_id}")
        return SuccessResponse.model_validate(data)
