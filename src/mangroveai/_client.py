from __future__ import annotations

from functools import cached_property
from typing import Any

import httpx

from ._config import ClientConfig
from ._transport._auth import ApiKeyAuth, NoAuth
from ._transport._http import HttpTransport
from ._transport._retry import RetryConfig
from ._transport._service import ServiceTransport
from .exceptions import ConfigurationError


class MangroveAI:
    """Synchronous MangroveAI SDK client.

    Provides typed access to the MangroveAI platform APIs including
    the core trading API and the Knowledge Base.

    Args:
        api_key: API key. Falls back to MANGROVE_API_KEY env var.
        environment: Target environment (dev/prod/local). Auto-detected from key prefix if omitted.
        base_url: Override the core API base URL.
        kb_base_url: Override the Knowledge Base API base URL.
        timeout: Default request timeout in seconds.
        max_retries: Maximum retry attempts on 429/5xx responses.
        auto_retry: Enable automatic retry with backoff on rate limits.
        auto_auth: Enable automatic JWT refresh on 401 responses.
        wallet_address: Wallet address for x402 payment-gated endpoints.
        httpx_client: Inject a custom httpx.Client for testing.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        environment: str | None = None,
        base_url: str | None = None,
        kb_base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        auto_retry: bool = True,
        auto_auth: bool = True,
        wallet_address: str | None = None,
        httpx_client: httpx.Client | None = None,
    ) -> None:
        self._config = ClientConfig(
            api_key=api_key,
            environment=environment,
            base_url=base_url,
            kb_base_url=kb_base_url,
            timeout=timeout,
            max_retries=max_retries,
            auto_retry=auto_retry,
            auto_auth=auto_auth,
            wallet_address=wallet_address,
        )

        from ._transport._mock import MockTransport

        retry = RetryConfig(max_retries=max_retries, auto_retry=auto_retry)

        if isinstance(httpx_client, MockTransport):
            self._http = httpx_client
        else:
            self._http = HttpTransport(timeout=timeout, retry_config=retry, httpx_client=httpx_client)

        auth = ApiKeyAuth(self._config.api_key) if self._config.api_key else NoAuth()

        self._core_transport = ServiceTransport(self._http, self._config.core_base_url, auth)
        self._core_v2_transport = ServiceTransport(self._http, self._config.core_v2_base_url, auth)
        self._kb_transport = ServiceTransport(self._http, self._config.kb_base_url, NoAuth())

    # -- Layer 1: Core API services --

    @cached_property
    def auth(self) -> Any:
        from ._services.auth import AuthService
        return AuthService(self._core_transport)

    @cached_property
    def strategies(self) -> Any:
        from ._services.strategies import StrategiesService
        return StrategiesService(self._core_transport)

    @cached_property
    def backtesting(self) -> Any:
        from ._services.backtesting import BacktestingService
        return BacktestingService(self._core_transport, self._core_v2_transport)

    @cached_property
    def signals(self) -> Any:
        from ._services.signals import SignalsService
        return SignalsService(self._core_transport)

    @cached_property
    def crypto_assets(self) -> Any:
        from ._services.crypto_assets import CryptoAssetsService
        return CryptoAssetsService(self._core_transport)

    @cached_property
    def execution(self) -> Any:
        from ._services.execution import ExecutionService
        return ExecutionService(self._core_transport)

    @cached_property
    def docs(self) -> Any:
        from ._services.docs import DocsService
        return DocsService(self._core_transport)

    # -- Layer 2: Knowledge Base --

    @cached_property
    def kb(self) -> Any:
        from ._services.kb import KBNamespace
        return KBNamespace(self._kb_transport)

    # -- Layer 3: Stubs --

    @cached_property
    def on_chain(self) -> Any:
        from ._services.on_chain import OnChainService
        return OnChainService(self._core_transport)

    @cached_property
    def defi(self) -> Any:
        from ._services.defi import DeFiService
        return DeFiService(self._core_transport)

    @cached_property
    def social(self) -> Any:
        from ._services.social import SocialService
        return SocialService(self._core_transport)

    # -- Utilities --

    def configure_service(self, service_name: str, base_url: str) -> None:
        """Override the base URL for a named service at runtime."""
        transports = {
            "core": self._core_transport,
            "core_v2": self._core_v2_transport,
            "kb": self._kb_transport,
        }
        transport = transports.get(service_name)
        if transport is None:
            raise ConfigurationError(f"Unknown service: {service_name}. Valid: {list(transports.keys())}")
        transport.base_url = base_url

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> MangroveAI:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
