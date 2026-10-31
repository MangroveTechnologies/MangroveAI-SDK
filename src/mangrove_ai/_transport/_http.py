from __future__ import annotations

import logging
import sys
from http.cookies import SimpleCookie
from typing import Any

import httpx

from .._version import __version__
from ..exceptions import (
    STATUS_CODE_EXCEPTIONS,
    APIError,
    ConnectionError,
    MalformedResponseError,
    ServerError,
    TimeoutError,
)
from ._protocol import TransportResponse
from ._retry import RetryConfig

logger = logging.getLogger(__name__)


class HttpTransport:
    """Synchronous HTTP transport backed by httpx."""

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        retry_config: RetryConfig | None = None,
        httpx_client: httpx.Client | None = None,
    ) -> None:
        self._retry = retry_config or RetryConfig()
        self._timeout = timeout
        self._client = httpx_client or httpx.Client(
            timeout=timeout,
            headers={
                "Content-Type": "application/json",
                "User-Agent": f"mangrove-sdk/{__version__} python/{sys.version_info.major}.{sys.version_info.minor}",
            },
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        timeout: float | None = None,
    ) -> TransportResponse:
        last_error: Exception | None = None

        for attempt in range(self._retry.max_retries + 1):
            try:
                response = self._client.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json,
                    timeout=self._timeout if timeout is None else timeout,
                )
            except httpx.ConnectError as e:
                raise ConnectionError(f"Connection failed: {e}") from e
            except httpx.TimeoutException as e:
                raise TimeoutError(f"Request timed out: {e}") from e

            if 200 <= response.status_code < 300:
                try:
                    data = response.json() if response.content else None
                except ValueError:
                    raise MalformedResponseError("Successful response did not contain valid JSON.") from None
                return TransportResponse(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    data=data,
                    text=response.text,
                )

            retry_after = self._parse_retry_after(response)
            if self._retry.should_retry(response.status_code, attempt, method):
                last_error = self._build_error(response)
                self._retry.wait(attempt, retry_after)
                continue

            raise self._build_error(response)

        if last_error is not None:
            raise last_error
        raise ServerError(500, "internal_error", "Max retries exceeded", "MAX_RETRIES")

    def close(self) -> None:
        self._client.close()

    def get_csrf_token(self, url: str) -> str | None:
        """Read the CSRF cookie that httpx would send to this exact endpoint."""
        request = self._client.build_request("POST", url)
        cookies: SimpleCookie[str] = SimpleCookie()
        cookies.load(request.headers.get("Cookie", ""))
        csrf = cookies.get("mg_csrf")
        return csrf.value if csrf is not None else None

    def _build_error(self, response: httpx.Response) -> APIError:
        try:
            body = response.json()
            if not isinstance(body, dict):
                raise ValueError
            error = body.get("error", "unknown_error")
            message = body.get("message", body.get("detail", "API request failed"))
            code = body.get("code", "UNKNOWN")
            correlation_id = body.get("correlation_id")
        except Exception:
            error = "unknown_error"
            message = "API request failed without a structured error response"
            code = "UNKNOWN"
            correlation_id = None
            body = {}

        # Servers can reflect request values. Keep structured diagnostics but
        # never include the caller's actual credentials in an exception string.
        secrets = []
        authorization = response.request.headers.get("Authorization", "")
        if authorization:
            secrets.append(authorization)
            secrets.append(authorization.partition(" ")[2])
        cookie_values: SimpleCookie[str] = SimpleCookie()
        cookie_values.load(response.request.headers.get("Cookie", ""))
        secrets.extend(cookie.value for cookie in cookie_values.values())

        def safe(value: Any, default: str) -> str:
            text = value if isinstance(value, str) else default
            for secret in secrets:
                if secret:
                    text = text.replace(secret, "[REDACTED]")
            return text

        exc_class = STATUS_CODE_EXCEPTIONS.get(response.status_code)
        if exc_class is None:
            exc_class = ServerError if response.status_code >= 500 else APIError

        return exc_class(
            status_code=response.status_code,
            error=safe(error, "unknown_error"),
            message=safe(message, "API request failed"),
            code=safe(code, "UNKNOWN"),
            correlation_id=safe(correlation_id, "") or None,
            retry_after=self._parse_retry_after(response),
            limit_kind=safe(body.get("limit_kind"), "") or None,
            resource_type=safe(body.get("resource_type"), "") or None,
        )

    def _parse_retry_after(self, response: httpx.Response) -> int | None:
        header = response.headers.get("Retry-After")
        if header is not None:
            try:
                return int(header)
            except ValueError:
                pass
        try:
            body = response.json()
            return body.get("retry_after")
        except Exception:
            return None
