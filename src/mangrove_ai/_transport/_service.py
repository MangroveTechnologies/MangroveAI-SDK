from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..exceptions import AuthenticationError
from ._auth import AuthStrategy, JWTAuth
from ._protocol import Transport, TransportResponse


class ServiceTransport:
    """Wraps a Transport with a base URL and auth strategy.

    Each service (strategies, signals, kb, etc.) gets its own ServiceTransport
    pre-configured with the correct base URL and auth.
    """

    def __init__(self, transport: Transport, base_url: str, auth: AuthStrategy) -> None:
        self._transport = transport
        self._base_url = base_url.rstrip("/")
        self._auth = auth
        self._refresh_session: Callable[[], None] | None = None

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> TransportResponse:
        url = f"{self._base_url}{path}"
        merged_headers = dict(headers) if headers else {}
        merged_headers = self._auth.apply(merged_headers)

        try:
            return self._transport.request(
                method, url, headers=merged_headers, params=params, json=json, timeout=timeout,
            )
        except AuthenticationError:
            # API keys cannot refresh. A session's authenticated failure can be
            # retried once after cookie-based refresh, retaining the same body
            # and operation identity. The refresh endpoint never recurses.
            if not isinstance(self._auth, JWTAuth) or self._refresh_session is None or path == "/auth/refresh":
                raise
            self._refresh_session()
            return self._transport.request(
                method, url, headers=self._auth.apply(dict(headers or {})),
                params=params, json=json, timeout=timeout,
            )

    def set_auth(self, auth: AuthStrategy) -> None:
        self._auth = auth

    def set_session_refresh(self, callback: Callable[[], None] | None) -> None:
        self._refresh_session = callback

    def get_csrf_token(self, path: str) -> str | None:
        reader = getattr(self._transport, "get_csrf_token", None)
        return reader(f"{self._base_url}{path}") if reader is not None else None

    @property
    def base_url(self) -> str:
        return self._base_url

    @base_url.setter
    def base_url(self, value: str) -> None:
        self._base_url = value.rstrip("/")

    def close(self) -> None:
        self._transport.close()
