from __future__ import annotations


class MangroveSDKError(Exception):
    """Base exception for all SDK errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class APIError(MangroveSDKError):
    """Server returned a non-2xx response with a parseable error body."""

    def __init__(
        self,
        status_code: int,
        error: str,
        message: str,
        code: str,
        correlation_id: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        self.status_code = status_code
        self.error = error
        self.code = code
        self.correlation_id = correlation_id
        self.retry_after = retry_after
        super().__init__(message)

    def __str__(self) -> str:
        base = f"[{self.status_code}] {self.code}: {self.message}"
        if self.correlation_id:
            base += f" (correlation_id={self.correlation_id})"
        return base


class AuthenticationError(APIError):
    """401 Unauthorized."""
    pass


class AuthorizationError(APIError):
    """403 Forbidden."""
    pass


class NotFoundError(APIError):
    """404 Not Found."""
    pass


class ValidationError(APIError):
    """400 Bad Request."""
    pass


class RateLimitError(APIError):
    """429 Too Many Requests."""
    pass


class ServerError(APIError):
    """5xx Server Error."""
    pass


class ServiceUnavailableError(APIError):
    """503 Service Unavailable."""
    pass


class ConnectionError(MangroveSDKError):
    """Network-level error."""
    pass


class TimeoutError(MangroveSDKError):
    """Request timeout."""
    pass


class ConfigurationError(MangroveSDKError):
    """Invalid SDK configuration."""
    pass


class NotImplementedLayerError(MangroveSDKError):
    """Raised for Layer 3 methods whose server endpoints do not yet exist."""
    pass


STATUS_CODE_EXCEPTIONS: dict[int, type[APIError]] = {
    400: ValidationError,
    401: AuthenticationError,
    403: AuthorizationError,
    404: NotFoundError,
    429: RateLimitError,
    503: ServiceUnavailableError,
}
