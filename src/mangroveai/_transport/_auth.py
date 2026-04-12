from __future__ import annotations

from typing import Protocol


class AuthStrategy(Protocol):
    """Strategy for applying authentication to request headers."""

    def apply(self, headers: dict[str, str]) -> dict[str, str]: ...


class ApiKeyAuth:
    """Authorization: Bearer {api_key}"""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def apply(self, headers: dict[str, str]) -> dict[str, str]:
        headers["Authorization"] = f"Bearer {self._api_key}"
        return headers


class JWTAuth:
    """Authorization: Bearer {jwt_access_token} with refresh support."""

    def __init__(self, access_token: str, refresh_token: str | None = None) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token

    def apply(self, headers: dict[str, str]) -> dict[str, str]:
        headers["Authorization"] = f"Bearer {self.access_token}"
        return headers


class NoAuth:
    """No authentication headers."""

    def apply(self, headers: dict[str, str]) -> dict[str, str]:
        return headers


class X402Auth:
    """X-Wallet-Address header for x402 payment-gated endpoints."""

    def __init__(self, wallet_address: str) -> None:
        self._wallet_address = wallet_address

    def apply(self, headers: dict[str, str]) -> dict[str, str]:
        headers["X-Wallet-Address"] = self._wallet_address
        return headers
