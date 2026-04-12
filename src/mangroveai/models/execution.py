from __future__ import annotations

from typing import Any

from ._base import MangroveModel


class CreateAccountRequest(MangroveModel):
    """Request body for creating a trading account."""

    account_type: str
    name: str | None = None
    initial_balance: float | None = None
    min_balance_threshold: float | None = None
    min_trade_amount: float | None = None
    max_open_positions: int | None = None
    max_trades_per_day: int | None = None
    max_risk_per_trade: float | None = None
    risk_params: dict[str, Any] | None = None


class Account(MangroveModel):
    """A trading account (paper or live)."""

    id: str
    org_id: str
    user_id: str
    account_type: str
    name: str | None = None
    cash_balance: float
    account_value: float
    min_balance_threshold: float | None = None
    min_trade_amount: float | None = None
    max_open_positions: int | None = None
    max_trades_per_day: int | None = None
    max_risk_per_trade: float | None = None
    risk_params: dict[str, Any] | None = None
    active: bool = True
    created_at: str | None = None
    updated_at: str | None = None


class Position(MangroveModel):
    """A trading position."""

    id: str
    org_id: str | None = None
    user_id: str | None = None
    account_id: str
    strategy_id: str | None = None
    asset: str
    exchange: str | None = None
    entry_price: float
    exit_price: float | None = None
    position_size: float
    cost: float | None = None
    value_at_close: float | None = None
    open: bool
    exit_reason: str | None = None
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    created_at: str | None = None
    entry_timestamp: str | None = None
    exit_timestamp: str | None = None


class Trade(MangroveModel):
    """A completed trade record."""

    id: str
    org_id: str | None = None
    user_id: str | None = None
    account_id: str | None = None
    position_id: str | None = None
    outcome: str
    profit_loss: float
    profit_loss_pct: float | None = None
    asset: str
    exchange: str | None = None
    strategy_name: str | None = None
    entry_price: float
    exit_price: float
    position_size: float
    beginning_balance: float | None = None
    ending_balance: float | None = None
    closed_at: str | None = None


class EvaluateResult(MangroveModel):
    """Result of evaluating a strategy against current market data."""

    success: bool
    strategy_id: str | None = None
    strategy_name: str | None = None
    asset: str | None = None
    current_price: float | None = None
    timestamp: str | None = None
    execution_state: dict[str, Any] | None = None
    new_orders: list[dict[str, Any]] | None = None
    execution_time_seconds: float | None = None
