from __future__ import annotations

from enum import Enum


class Environment(str, Enum):
    DEV = "dev"
    PROD = "prod"
    LOCAL = "local"

    def __str__(self) -> str:
        return self.value


DEFAULT_URLS: dict[str, dict[str, str]] = {
    Environment.DEV: {
        # No verified public development API origin is currently available.
        # ClientConfig requires an explicit origin instead of using production.
        "core": "",
        "core_v2": "",
        "kb": "https://devkb.mangrove.trade/api",
    },
    Environment.PROD: {
        "core": "https://api.mangrovedeveloper.ai/api/v1",
        "core_v2": "https://api.mangrovedeveloper.ai/api/v2",
        "kb": "https://kb.mangrovedeveloper.ai/api",
    },
    Environment.LOCAL: {
        "core": "http://localhost:5001/api/v1",
        "core_v2": "http://localhost:5001/api/v2",
        "kb": "http://localhost:8080/api",
    },
}

DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
USER_AGENT_PREFIX = "mangrove-sdk"

# API key prefix -> environment mapping
KEY_PREFIX_ENV: dict[str, Environment] = {
    "dev_": Environment.DEV,
    "prod_": Environment.PROD,
    "local_": Environment.LOCAL,
}
