from __future__ import annotations

from typing import Any

from ..models.auth import ApiKey, ApiKeyCreateResponse, LoginResponse, RefreshResponse
from ..models.shared import SuccessResponse
from ._base import BaseService


class AuthService(BaseService):
    """Authentication and API key management."""

    def login(self, firebase_token: str) -> LoginResponse:
        """Exchange a Firebase ID token for MangroveAI JWT tokens.

        Args:
            firebase_token: Firebase ID token from Google OAuth.

        Returns:
            LoginResponse with access_token, refresh_token, and user info.
        """
        data = self._request("POST", "/auth/login", json={"firebase_token": firebase_token})
        return LoginResponse.model_validate(data)

    def refresh(self, refresh_token: str) -> RefreshResponse:
        """Refresh an expired access token.

        Args:
            refresh_token: The refresh token from a previous login.

        Returns:
            RefreshResponse with a new access_token.
        """
        data = self._request("POST", "/auth/refresh", json={"refresh_token": refresh_token})
        return RefreshResponse.model_validate(data)

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
