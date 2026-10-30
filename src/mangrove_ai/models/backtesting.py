from __future__ import annotations

import warnings
from typing import Any

from pydantic import model_validator

from ._base import MangroveModel

# Fields superseded by cooldown_config in SDK 0.2.0.
_DEPRECATED_COOLDOWN_FIELDS = ("cooldown_bars", "daily_momentum_limit", "weekly_momentum_limit", "max_hold_time_hours")

_DEPRECATION_MSG = (
    "The top-level field '{field}' is deprecated and will be removed in a future major version. "
    "For the bars model use cooldown_config, keyed by primary timeframe "
    "(e.g. '5m', '15m', '1h', '1d'). Trades-model breaker keys belong in "
    "execution_config.circuit_breaker, not in cooldown_config."
)


def _warn_deprecated_fields(values: Any) -> Any:
    """Emit DeprecationWarning for each legacy top-level cooldown field that is explicitly set."""
    for field in _DEPRECATED_COOLDOWN_FIELDS:
        if getattr(values, field, None) is not None:
            warnings.warn(_DEPRECATION_MSG.format(field=field), DeprecationWarning, stacklevel=3)
    return values


class BacktestRequest(MangroveModel):
    """Request body for running a single backtest.

    `interval` is required. Provide exactly one of `strategy_json` (full config
    inline) or `strategy_id` (reuse a saved strategy by UUID -- the server loads
    its `strategy_json` and defaults `asset` from the saved strategy). `asset` is
    required only when using `strategy_json`. Every other trading-config field is
    optional -- the server fills it from `trading_defaults.json` when omitted.
    Fetch the canonical defaults via ``client.config.execution_defaults()``.
    (strategy_id added in MangroveAI #629; mirrors run_bulk's strategy_ids and
    execution.evaluate(strategy_id).)
    """

    asset: str | None = None
    interval: str
    # Provide exactly one of strategy_json or strategy_id (see class docstring).
    strategy_json: str | None = None
    strategy_id: str | None = None
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
    cooldown_model: str | None = None
    # The service nests these options in execution_config, where the engine
    # reads them. Omission accepts defaults; explicit None disables a guard.
    max_drawdown_limit: float | None = None
    max_drawdown_halt_limit: float | None = None
    cooldown_config: dict[str, dict[str, Any]] | None = None
    """Legacy per-timeframe window configuration for cooldown_model='bars'.

    Keyed by primary timeframe string, e.g. "5m", "15m", "1h", "1d".
    Fetch the complete legacy shape from client.config.execution_defaults().
    It contains short_loss_limit, long_loss_limit, short_window_bars,
    long_window_bars, short_cooldown_bars, and long_cooldown_bars.

    The default trades model instead reads a flat execution_config.circuit_breaker
    block: consecutive_loss_limit, loss_amount_pct, pause_bars, pause_min_hours,
    pause_max_days, max_consecutive_pauses, resume_trades, resume_size_fraction,
    drawdown_pause_bars. A partial breaker block retains omitted server defaults.
    Its loss pause defaults to 36 bars, clamped to 24 hours through 14 days;
    drawdown pauses default to 72 bars. The two drawdown thresholds are separate
    execution_config fields, not members of the circuit_breaker block.

    The old top-level fields (cooldown_bars, daily_momentum_limit, weekly_momentum_limit,
    max_hold_time_hours) remain accepted during the deprecation grace period but will be
    removed in a future major version.
    """

    @model_validator(mode="after")
    def _check_deprecated_fields(self) -> BacktestRequest:
        return _warn_deprecated_fields(self)

    @model_validator(mode="after")
    def _check_strategy_source(self) -> BacktestRequest:
        if bool(self.strategy_json) == bool(self.strategy_id):
            raise ValueError("Provide exactly one of strategy_json or strategy_id")
        if self.strategy_json and not self.asset:
            raise ValueError("asset is required when using strategy_json")
        return self


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
    cooldown_model: str | None = None
    max_drawdown_limit: float | None = None
    max_drawdown_halt_limit: float | None = None
    cooldown_config: dict[str, dict[str, Any]] | None = None
    """Per-timeframe cooldown configuration. See BacktestRequest.cooldown_config for full docs."""

    @model_validator(mode="after")
    def _check_deprecated_fields(self) -> BulkBacktestRequest:
        return _warn_deprecated_fields(self)


class BacktestResult(MangroveModel):
    """Result of a backtest run.

    Two server shapes land here:

    - a run result (``run()`` / ``run_async()`` / the legacy sync route), which
      carries ``success``;
    - a stored run record from ``GET /backtests/{id}`` (``get()``), which carries
      ``id`` / ``status`` / ``error_message`` and the run's ``config`` and window
      but no ``success``.

    For a stored record, ``success`` is derived from ``status`` (``completed`` ->
    True, ``failed`` -> False, anything still in flight -> None), ``error`` from
    ``error_message``, and ``trade_count`` from ``trade_history``. Before this,
    ``success`` was required and every ``get()`` on a real run raised a
    ValidationError.
    """

    success: bool | None = None
    metrics: dict[str, Any] | None = None
    trade_history: list[dict[str, Any]] | None = None
    execution_time_seconds: float | None = None
    trade_count: int | None = None
    strategy_names: list[str] | None = None
    error: str | None = None

    # Stored run record fields (GET /backtests/{id}).
    id: str | None = None
    status: str | None = None
    asset: str | None = None
    strategy_id: str | None = None
    config: dict[str, Any] | None = None
    error_message: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    initial_balance: float | None = None

    @model_validator(mode="before")
    @classmethod
    def _derive_from_stored_record(cls, data: Any) -> Any:
        if not isinstance(data, dict) or data.get("success") is not None:
            return data
        data = dict(data)
        status = data.get("status")
        if status == "completed":
            data["success"] = True
        elif status == "failed":
            data["success"] = False
        if data.get("error") is None and data.get("error_message"):
            data["error"] = data["error_message"]
        if data.get("trade_count") is None and isinstance(data.get("trade_history"), list):
            data["trade_count"] = len(data["trade_history"])
        return data


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


class BacktestArchiveResult(MangroveModel):
    """Response from archiving or unarchiving a backtest.

    Backtests are never deleted; archiving hides a run from the default history
    view (and is reversible via unarchive).
    """

    success: bool
    backtest_id: str
    archived: bool


class Benchmark(MangroveModel):
    """Buy-and-hold return over a window (``client.backtesting.get_benchmark``).

    Same fields as the copilot's ``get_benchmark`` tool, plus
    ``buy_and_hold_return_raw`` for arithmetic.
    """

    asset: str
    start: str
    end: str
    bars: int
    """How many daily closes it was computed from."""
    first_close: float
    last_close: float
    buy_and_hold_return: str | None = None
    """Display string with the % attached, e.g. ``"12.3456%"``."""
    buy_and_hold_return_raw: float | None = None
    """The same return as a number on a 0-100 percent scale (``12.3456`` means 12.3456%)."""
    unit: str = "percent_0_100"
    base_token: str | None = None
    quote_token: str | None = None
    market_data_venue: str | None = None
    requested_start: str | None = None
    requested_end: str | None = None
    interval: str | None = None
    partial: bool | None = None
    has_gaps: bool | None = None


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
