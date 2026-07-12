from __future__ import annotations

import logging
import os

from ._constants import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT, DEFAULT_URLS, KEY_PREFIX_ENV, Environment

logger = logging.getLogger(__name__)


def _maybe_load_dotenv() -> None:
    """Best-effort load of a ``.env`` file into ``os.environ`` (soft dependency).

    ``python-dotenv`` is an *optional* dependency (``pip install mangroveai[dotenv]``).
    If it isn't installed this is a no-op, so the SDK keeps reading ``os.environ``
    exactly as before for users who don't opt in.

    ``override=False`` guarantees that variables already present in the real
    process environment always win over values in a ``.env`` file — so this never
    changes behavior for users who rely on real env vars.
    """
    try:
        from dotenv import find_dotenv, load_dotenv
    except ImportError:
        logger.debug("python-dotenv not installed; skipping .env autoload")
        return

    load_dotenv(find_dotenv(usecwd=True), override=False)


class ClientConfig:
    """Resolved SDK configuration.

    Resolution precedence:
    1. Explicit constructor arguments (highest)
    2. Environment variables (real process env, then optionally a .env file)
    3. Auto-detection from API key prefix
    4. Defaults (lowest)

    If ``python-dotenv`` is installed (``pip install mangroveai[dotenv]``) and
    ``load_dotenv`` is left enabled, a ``.env`` file discovered from the current
    working directory is loaded into the environment before resolution. Real
    process environment variables always take precedence over ``.env`` values.
    """

    def __init__(
        self,
        api_key: str | None = None,
        environment: str | None = None,
        base_url: str | None = None,
        kb_base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        auto_retry: bool = True,
        auto_auth: bool = True,
        wallet_address: str | None = None,
        load_dotenv: bool = True,
    ) -> None:
        if load_dotenv:
            _maybe_load_dotenv()

        self.api_key = api_key or os.environ.get("MANGROVE_API_KEY")
        self.timeout = timeout
        self.max_retries = max_retries
        self.auto_retry = auto_retry
        self.auto_auth = auto_auth
        self.wallet_address = wallet_address or os.environ.get("MANGROVE_WALLET_ADDRESS")

        self.environment = self._resolve_environment(environment)
        env_urls = DEFAULT_URLS[self.environment]

        self.core_base_url = base_url or os.environ.get("MANGROVE_BASE_URL") or env_urls["core"]
        self.core_v2_base_url = base_url.replace("/v1", "/v2") if base_url else env_urls["core_v2"]
        self.kb_base_url = kb_base_url or os.environ.get("MANGROVE_KB_BASE_URL") or env_urls["kb"]

    def _resolve_environment(self, explicit: str | None) -> str:
        if explicit:
            return explicit

        env_var = os.environ.get("MANGROVE_ENVIRONMENT")
        if env_var:
            return env_var

        if self.api_key:
            for prefix, env in KEY_PREFIX_ENV.items():
                if self.api_key.startswith(prefix):
                    return env

        return Environment.PROD
