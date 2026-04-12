from __future__ import annotations

from typing import Any

from ._base import MangroveModel


class BacktestRequest(MangroveModel):
    """Request body for running a single backtest."""

    asset: str
    interval: str
    strategy_json: str
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
    volatility_mode: str = "stddev"
    enable_volatility_adjustment: bool = False
    cooldown_bars: int = 24
    daily_momentum_limit: float = 3.0
    weekly_momentum_limit: float = 3.0
    lookback_months: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    slippage_pct: float | None = None
    fee_pct: float | None = None
    execution_config: dict[str, Any] | None = None
    data_source: str | None = None


class BulkBacktestRequest(MangroveModel):
    """Request body for running bulk backtests."""

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
    volatility_mode: str = "stddev"
    enable_volatility_adjustment: bool = False
    cooldown_bars: int = 24
    daily_momentum_limit: float = 3.0
    weekly_momentum_limit: float = 3.0
    interval: str = "1h"
    strategy_ids: list[str] | None = None
    strategy_configs: list[dict[str, Any]] | None = None
    slippage_pct: float | None = None
    fee_pct: float | None = None
    execution_config: dict[str, Any] | None = None


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
