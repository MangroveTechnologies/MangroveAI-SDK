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
    # Stateless lane only: present when the request carried caller-owned
    # open_positions. The UPDATED set (surviving + newly entered, resting
    # bracket orders included) -- persist it and echo it back on the next
    # evaluation, exactly like execution_state.
    open_positions: list[dict[str, Any]] | None = None
    execution_time_seconds: float | None = None
    error: str | None = None


class BulkEvaluateResult(MangroveModel):
    """Envelope for bulk strategy evaluation.

    ``results`` carries one ``EvaluateResult``-shaped entry per input
    strategy (in the same order as the request). Per-strategy failures
    are captured in each entry's ``error`` field without aborting the
    batch — check ``results[i].success`` per row.

    ``data_fetches`` is the number of unique ``(asset, timeframe)``
    market-data API calls the server actually made. Bulk evaluation
    shares fetches across strategies that need the same OHLCV slice,
    so this number is typically ≪ ``len(results)``.

    ``error`` is set only when the batch itself failed to start
    (e.g. malformed top-level body); in that case ``success=False``
    and ``results=[]``.
    """

    success: bool
    results: list[EvaluateResult] = []
    data_fetches: int = 0
    total_execution_time_seconds: float = 0.0
    error: str | None = None


# ---------------------------------------------------------------------------
# Portfolio (batch dashboard read)
# ---------------------------------------------------------------------------


class PortfolioRecentTrade(MangroveModel):
    """One trade entry inside `PortfolioEntry.recent_trades` — last 5
    trades for a given strategy.
    """

    id: str | None = None
    asset: str | None = None
    outcome: str | None = None
    profit_loss: float | None = None
    profit_loss_pct: float | None = None
    closed_at: str | None = None


class PortfolioEntry(MangroveModel):
    """Dashboard-ready snapshot for one strategy.

    Pulled by `get_portfolio(strategy_ids)`. Designed for UI cards that
    need a strategy's name + asset + status + most-recent execution
    state + last 5 trades in one batched read instead of an N+1 RTT
    fan-out.

    Field names mirror the server response shape verbatim — most
    notably ``strategy_name`` (not ``name``) and ``open_positions_count``
    (not ``open_positions``). ``status`` is only populated when the
    server has it available (e.g. for non-archived strategies).
    """

    strategy_id: str
    strategy_name: str | None = None
    asset: str | None = None
    status: str | None = None
    execution_state: dict[str, Any] | None = None
    last_evaluated_at: str | None = None
    open_positions_count: int | None = None
    recent_trades: list[PortfolioRecentTrade] = []


class PortfolioResponse(MangroveModel):
    """Envelope returned by `GET /execution/portfolio`.

    ``results`` is the list of strategies the server found (in request
    order, with missing ones omitted). ``missing`` lists IDs that did
    not match any strategy the caller has access to — useful for
    distinguishing "deleted" from "no permission".
    """

    results: list[PortfolioEntry] = []
    missing: list[str] = []
