"""Config service — read-only server configuration (trading defaults + execution defaults).

Corresponds to the `/api/v1/config/*` endpoints added in MangroveAI #456.
These are the authoritative defaults the server falls back to when a request
omits optional fields. Clients can fetch them instead of hardcoding copies.
"""
from __future__ import annotations

from typing import Any

from ._base import BaseService


class ConfigService(BaseService):
    """Server configuration — trading defaults + flattened execution config.

    Both endpoints are unauthenticated (non-secret public configuration).
    """

    def trading_defaults(self) -> dict[str, Any]:
        """Return the full `trading_defaults.json` structure, nested sections intact.

        Shape (as of 2026-04-24):
            description, signal_defaults, backtest_defaults, risk_management,
            position_limits, volatility_settings, trading_rules, time_based_exits.

        Source of truth for every server-side default — use this instead of
        maintaining a parallel local copy.
        """
        return self._request("GET", "/config/trading-defaults")

    def execution_defaults(self) -> dict[str, Any]:
        """Return the flattened execution config the server applies by default.

        This is exactly what the backtest / strategy create routes use when a
        request omits `execution_config`. Convenient for prefilling a UI or
        for passing straight back as `BacktestRequest.execution_config`.

        The flat shape merges `risk_management`, `position_limits`,
        `volatility_settings`, `trading_rules`, and `time_based_exits` from
        trading_defaults.json. `signal_defaults` and `backtest_defaults` are
        intentionally excluded.
        """
        return self._request("GET", "/config/execution-defaults")
