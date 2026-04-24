from __future__ import annotations

import warnings
from typing import Any

from pydantic import model_validator

from ._base import MangroveModel

# Fields superseded by cooldown_config in SDK 0.2.0.
_DEPRECATED_COOLDOWN_FIELDS = ("cooldown_bars", "daily_momentum_limit", "weekly_momentum_limit", "max_hold_time_hours")

_DEPRECATION_MSG = (
    "The top-level field '{field}' is deprecated and will be removed in a future major version. "
    "Use cooldown_config instead. cooldown_config is a dict keyed by primary timeframe "
    "(e.g. '5m', '15m', '1h', '1d'), where each value is a dict with: "
    "max_hold_time_hours, short_loss_limit, long_loss_limit, short_window_bars, long_window_bars."
)


def _warn_deprecated_fields(values: Any) -> Any:
    """Emit DeprecationWarning for each legacy top-level cooldown field that is explicitly set."""
    for field in _DEPRECATED_COOLDOWN_FIELDS:
        if getattr(values, field, None) is not None:
            warnings.warn(_DEPRECATION_MSG.format(field=field), DeprecationWarning, stacklevel=3)
    return values


class BacktestRequest(MangroveModel):
    """Request body for running a single backtest.

    `asset`, `interval`, and `strategy_json` are strategy-specific and remain
    required. Every other trading-config field is now optional — the server
    fills it from `trading_defaults.json` when omitted. Fetch the canonical
    defaults via ``client.config.execution_defaults()`` if you need to
    inspect or override them. Explicit values you pass still win. (SDK 0.3.0
    / MangroveAI #437.)
    """

    asset: str
    interval: str
    strategy_json: str
    # Server-default fillable: None = accept server default (from
    # trading_defaults.json). See client.config.execution_defaults() for the
    # authoritative values.
    initial_balance: float | None = None
    min_balance_threshold: float | None = None
    min_trade_amount: float | None = None
    max_open_positions: int | None = None
    max_trades_per_day: int | None = None
    max_risk_per_trade: float | None = None
    max_units_per_trade: float | None = None
    max_trade_amount: float | None = None
    volatility_window: int | None = None
    target_volatility: float | None = None
    volatility_mode: str = "stddev"
    enable_volatility_adjustment: bool = False
    cooldown_bars: int = 24
    daily_momentum_limit: float = 3.0
    weekly_momentum_limit: float = 3.0
    max_hold_time_hours: float | None = None
    lookback_months: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    slippage_pct: float | None = None
    fee_pct: float | None = None
    execution_config: dict[str, Any] | None = None
    data_source: str | None = None
    cooldown_config: dict[str, dict[str, Any]] | None = None
    """Per-timeframe cooldown configuration (preferred over legacy top-level fields).

    Keyed by primary timeframe string, e.g. "5m", "15m", "1h", "1d".
    Each value is a dict with the following keys:
      - max_hold_time_hours (int): maximum bars a position may be held
      - short_loss_limit (int): number of losses in the short window that triggers a short cooldown
      - long_loss_limit (int): number of losses in the long window that triggers a long cooldown
      - short_window_bars (int): rolling lookback bars AND cooldown duration for the short tier
      - long_window_bars (int): rolling lookback bars AND cooldown duration for the long tier

    Example::

        cooldown_config={
            "1h": {
                "max_hold_time_hours": 24,
                "short_loss_limit": 4,
                "long_loss_limit": 6,
                "short_window_bars": 48,
                "long_window_bars": 144,
            }
        }

    The old top-level fields (cooldown_bars, daily_momentum_limit, weekly_momentum_limit,
    max_hold_time_hours) remain accepted during the deprecation grace period but will be
    removed in a future major version.
    """

    @model_validator(mode="after")
    def _check_deprecated_fields(self) -> BacktestRequest:
        return _warn_deprecated_fields(self)


class BulkBacktestRequest(MangroveModel):
    """Request body for running bulk backtests.

    `start_date` and `end_date` remain required; every trading-config field
    is now optional and falls back to the server's `trading_defaults.json`
    when omitted. See ``client.config.execution_defaults()``. (SDK 0.3.0 /
    MangroveAI #437.)
    """

    start_date: str
    end_date: str
    # Server-default fillable — see BacktestRequest for the same pattern.
    initial_balance: float | None = None
    min_balance_threshold: float | None = None
    min_trade_amount: float | None = None
    max_open_positions: int | None = None
    max_trades_per_day: int | None = None
    max_risk_per_trade: float | None = None
    max_units_per_trade: float | None = None
    max_trade_amount: float | None = None
    volatility_window: int | None = None
    target_volatility: float | None = None
    volatility_mode: str = "stddev"
    enable_volatility_adjustment: bool = False
    cooldown_bars: int = 24
    daily_momentum_limit: float = 3.0
    weekly_momentum_limit: float = 3.0
    max_hold_time_hours: float | None = None
    interval: str = "1h"
    strategy_ids: list[str] | None = None
    strategy_configs: list[dict[str, Any]] | None = None
    slippage_pct: float | None = None
    fee_pct: float | None = None
    execution_config: dict[str, Any] | None = None
    cooldown_config: dict[str, dict[str, Any]] | None = None
    """Per-timeframe cooldown configuration. See BacktestRequest.cooldown_config for full docs."""

    @model_validator(mode="after")
    def _check_deprecated_fields(self) -> BulkBacktestRequest:
        return _warn_deprecated_fields(self)


class BacktestResult(MangroveModel):
    """Result of a completed backtest run."""

    success: bool
    metrics: dict[str, Any] | None = None
    trade_history: list[dict[str, Any]] | None = None
    execution_time_seconds: float | None = None
    trade_count: int | None = None
    strategy_names: list[str] | None = None
    error: str | None = None


class BulkBacktestItemResult(MangroveModel):
    """Result for a single strategy within a bulk backtest."""

    success: bool
    strategy_id: str | None = None
    strategy_name: str | None = None
    metrics: dict[str, Any] | None = None
    trade_count: int | None = None
    execution_time_seconds: float | None = None
    error: str | None = None


class BulkBacktestResult(MangroveModel):
    """Result of a bulk backtest run."""

    success: bool
    results: list[BulkBacktestItemResult]
    data_fetches: int | None = None
    total_execution_time_seconds: float | None = None


class BacktestTradesResponse(MangroveModel):
    """Trade history for a backtest."""

    success: bool
    backtest_id: str
    trade_count: int
    trades: list[dict[str, Any]]


class AsyncBacktestSubmission(MangroveModel):
    """Response from submitting an async backtest."""

    backtest_id: str
    status: str


class AsyncBacktestStatus(MangroveModel):
    """Status of an async backtest."""

    backtest_id: str
    status: str
    metrics: dict[str, Any] | None = None
    trade_history: list[dict[str, Any]] | None = None
    error_message: str | None = None
    execution_time_seconds: float | None = None
    created_at: str | None = None
    completed_at: str | None = None
