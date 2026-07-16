from __future__ import annotations

from typing import Any

from ._base import MangroveModel


class TokenBreakdown(MangroveModel):
    """Token usage broken down by category."""

    system_tokens: int | None = None
    context_tokens: int | None = None
    user_tokens: int | None = None
    assistant_tokens: int | None = None
    total_tokens: int | None = None


class UserMetrics(MangroveModel):
    """Usage metrics for the authenticated user.

    Returned by ``client.users.get_my_metrics()`` (GET /users/me/metrics).
    """

    conversations_count: int | None = None
    messages_count: int | None = None
    estimated_tokens: int | None = None
    token_breakdown: TokenBreakdown | None = None
    strategies_count: int | None = None
    backtests_count: int | None = None
    tool_calls: dict[str, Any] | None = None


class UserStrategy(MangroveModel):
    """A strategy owned by the authenticated user (GET /users/me/strategies)."""

    id: str | None = None
    name: str | None = None
    asset: str | None = None
    status: str | None = None
    entry_signals: list[str] | None = None
    exit_signals: list[str] | None = None
    created_at: str | None = None
    archived: bool | None = None
    archived_at: str | None = None
    config: dict[str, Any] | None = None


class UserBacktest(MangroveModel):
    """A backtest owned by the authenticated user (GET /users/me/backtests)."""

    id: str | None = None
    asset: str | None = None
    status: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    initial_balance: float | None = None
    total_return: float | None = None
    irr_annualized: float | None = None
    sharpe_ratio: float | None = None
    win_rate: float | None = None
    max_drawdown: float | None = None
    total_trades: int | None = None
    execution_time: float | None = None
    created_at: str | None = None
    archived: bool | None = None
    archived_at: str | None = None
    #: PASS / FAIL / INSUFFICIENT_TRADES, or the raw status for non-completed runs.
    result: str | None = None
    metrics: dict[str, Any] | None = None
    trade_history: Any | None = None
