from __future__ import annotations

from ._base import MangroveModel


class LoginUser(MangroveModel):
    """User info returned from login."""

    id: str
    name: str
    email: str
    org_id: str


class LoginResponse(MangroveModel):
    """Response from POST /auth/login."""

    success: bool
    access_token: str
    refresh_token: str
    user: LoginUser


class RefreshResponse(MangroveModel):
    """Response from POST /auth/refresh."""

    success: bool
    access_token: str


class ApiKey(MangroveModel):
    """An API key summary (masked)."""

    id: str
    key_prefix: str
    name: str
    created_at: str
    expires_at: str | None = None
    scopes: list[str] | None = None
    last_used_at: str | None = None
    revoked_at: str | None = None
    is_active: bool | None = None


class ApiKeyCreateResponse(MangroveModel):
    """Response from POST /auth/api-keys. Contains the full key (shown once)."""

    success: bool
    key: str
    key_id: str
    key_prefix: str
    name: str
    created_at: str
    expires_at: str | None = None
