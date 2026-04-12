"""MangroveAI Python SDK.

Quickstart:
    from mangroveai import MangroveAI

    client = MangroveAI(api_key="prod_a1b2c3...")
    strategies = client.strategies.list()
"""

from ._client import MangroveAI
from ._version import __version__
from .exceptions import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    ConnectionError,
    MangroveSDKError,
    NotFoundError,
    NotImplementedLayerError,
    RateLimitError,
    ServerError,
    ServiceUnavailableError,
    TimeoutError,
    ValidationError,
)

__all__ = [
    "__version__",
    "MangroveAI",
    "MangroveSDKError",
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "ServerError",
    "ServiceUnavailableError",
    "ConnectionError",
    "TimeoutError",
    "ConfigurationError",
    "NotImplementedLayerError",
]
