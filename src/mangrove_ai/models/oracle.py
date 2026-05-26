"""Models for the MangroveOracle endpoints reached via MangroveAI's reverse proxy.

The Oracle surface is exposed under MangroveAI at ``/api/v1/oracle/*``. This
module mirrors the Pydantic shapes Oracle itself ships (see
``MangroveOracle/src/models/sieve.py`` and ``data_query.py``) so the SDK can
validate request/response shapes without round-tripping through dynamic dicts.
"""
from __future__ import annotations

from typing import Any

from ._base import MangroveModel


# ---------------------------------------------------------------------------
# SIEVE classifier scoring
# ---------------------------------------------------------------------------

class SignalSpec(MangroveModel):
    """One entry or exit signal inside a `StrategyInput`."""

    name: str
    signal_type: str  # "TRIGGER" | "FILTER"
    timeframe: str | None = None
    params: dict[str, Any] = {}


class StrategyInput(MangroveModel):
    """MangroveAI-shaped strategy passed to SIEVE."""

    asset: str
    entry: list[SignalSpec]
    exit: list[SignalSpec]
    execution_config: dict[str, Any] | None = None


class RunInput(MangroveModel):
    """Raw run shape consumed by SIEVE — use when scoring rows already
    extracted from the Mangrove sweep corpus.
    """

    entry_json: str
    exit_json: str
    asset: str
    exec_config: dict[str, Any]


class SieveScoreRequest(MangroveModel):
    """Exactly one of `strategies` / `runs` must be set; ≤99 items per request."""

    strategies: list[StrategyInput] | None = None
    runs: list[RunInput] | None = None


class SievePrediction(MangroveModel):
    """Probabilities for one SIEVE-scored item.

    ``binary`` keys: ``p_no_trades`` + ``p_trades``.
    ``four_class`` keys: ``losing`` / ``no_trades`` / ``wash`` / ``winning``.
    Each dict sums to 1.0 within float32 tolerance.
    """

    binary: dict[str, float]
    four_class: dict[str, float]


class SieveScoreResponse(MangroveModel):
    """SIEVE score response with full provenance.

    ``model_version`` is a content hash of the bundled `.pt` + vocab files
    (format ``mangrove-sieve:<hash>``); changes when SIEVE is retrained.
    ``code_version`` is the Oracle dependency stack
    (``oracle:<ref> ai:<ref> kb:<ref> roots:<ref>``).
    """

    predictions: list[SievePrediction]
    count: int
    model_version: str
    code_version: str


# ---------------------------------------------------------------------------
# Data query
# ---------------------------------------------------------------------------

class DataQueryFilter(MangroveModel):
    """One filter clause on a data-query request."""

    col: str
    op: str  # "=", "!=", ">", ">=", "<", "<=", "in", "not in"
    value: Any


class DataQueryRequest(MangroveModel):
    """Query the corpus of Oracle backtest results / OHLCV bars.

    The proxy whitelists the columns and filter operators server-side; the
    request only ever sees the curated surface.
    """

    table: str  # "results" | "ohlcv"
    select: list[str]
    filters: list[DataQueryFilter] = []
    order_by: list[str] | None = None
    limit: int = 100
    offset: int = 0


class DataQueryResponse(MangroveModel):
    """Rows + metadata for a data-query response."""

    rows: list[dict[str, Any]]
    row_count: int
    table: str
    code_version: str | None = None


# ---------------------------------------------------------------------------
# Oracle backtests (sync / async / bulk)
# ---------------------------------------------------------------------------

class OracleBacktestRequest(MangroveModel):
    """Backtest a single strategy against Oracle's engine.

    Shape mirrors `MangroveOracle/src/api/routes/backtest.py:123-275`. Most
    risk-management fields can be omitted; the server fills from canonical
    `trading_defaults.json`.
    """

    asset: str
    interval: str
    strategy_json: str
    # Optional risk-mgmt / execution fields — server-default-fillable
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
    volatility_mode: str | None = None
    enable_volatility_adjustment: bool | None = None
    cooldown_bars: int | None = None
    daily_momentum_limit: float | None = None
    weekly_momentum_limit: float | None = None
    # Date-range mode (one of: start+end, start only, lookback_months, none)
    start_date: str | None = None
    end_date: str | None = None
    lookback_months: int | None = None
    exchange: str | None = None
    max_hold_time_hours: int | None = None
    slippage_pct: float | None = None
    fee_pct: float | None = None
    execution_config: dict[str, Any] | None = None
    # "full" (default) or "quick"
    mode: str | None = None


class OracleBulkBacktestRequest(MangroveModel):
    """Evaluate many strategies over a shared date range; one OHLCV fetch
    per unique (asset, timeframe).
    """

    start_date: str
    end_date: str
    initial_balance: float
    min_balance_threshold: float
    min_trade_amount: float
    max_open_positions: int
    max_trades_per_day: int
    max_risk_per_trade: float
    max_units_per_trade: float
    max_trade_amount: float
    volatility_window: int
    target_volatility: float
    volatility_mode: str
    enable_volatility_adjustment: bool
    cooldown_bars: int
    daily_momentum_limit: float
    weekly_momentum_limit: float
    strategy_ids: list[str] | None = None
    strategy_configs: list[dict[str, Any]] | None = None
    execution_config: dict[str, Any] | None = None
    max_hold_time_hours: int | None = None
    slippage_pct: float | None = None
    fee_pct: float | None = None
    mode: str | None = None


class OracleBacktestResult(MangroveModel):
    """Result of a single Oracle backtest."""

    success: bool
    metrics: dict[str, Any]
    execution_time_seconds: float | None = None
    trade_count: int | None = None
    strategy_names: list[str] | None = None
    trade_history: list[dict[str, Any]] | None = None
    denied_signals: list[dict[str, Any]] | None = None
    error: str | None = None


class OracleAsyncBacktestSubmission(MangroveModel):
    """202 Accepted shape for async backtest submission."""

    backtest_id: str
    status: str


class OracleAsyncBacktestStatus(MangroveModel):
    """Polling response for an async backtest."""

    backtest_id: str
    status: str
    metrics: dict[str, Any] | None = None
    trade_history: list[dict[str, Any]] | None = None
    execution_time_seconds: float | None = None
    trade_count: int | None = None
    strategy_names: list[str] | None = None
    error_message: str | None = None


class OracleBulkBacktestResult(MangroveModel):
    """Bulk backtest result envelope."""

    success: bool
    results: list[dict[str, Any]]
    data_fetches: int
    total_execution_time_seconds: float
    error: str | None = None
