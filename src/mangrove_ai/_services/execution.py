from __future__ import annotations

from typing import Any

from ..models.execution import (
    Account,
    BulkEvaluateResult,
    CreateAccountRequest,
    EvaluateResult,
    PortfolioResponse,
    Position,
    Trade,
)
from ._base import BaseService

# Server-side cap on `get_portfolio` strategy_ids per request. Enforced
# client-side too so callers fail fast with ValueError instead of an
# HTTP 400.
PORTFOLIO_MAX_IDS_PER_REQUEST = 100


class ExecutionService(BaseService):
    """Trading accounts, positions, trades, and strategy evaluation."""

    def list_accounts(self, *, account_type: str | None = None) -> list[Account]:
        """List trading accounts.

        Args:
            account_type: Filter by "paper" or "live".
        """
        params: dict[str, Any] = {}
        if account_type is not None:
            params["account_type"] = account_type
        data = self._request("GET", "/execution/accounts", params=params or None)
        items = data if isinstance(data, list) else data.get("accounts", data)
        return [Account.model_validate(a) for a in items]

    def create_account(self, request: CreateAccountRequest) -> Account:
        """Create a new trading account.

        Args:
            request: Account configuration.
        """
        return self._request_model(
            "POST", "/execution/accounts", Account,
            json=request.model_dump(exclude_none=True),
        )

    def get_account(self, account_id: str) -> Account:
        """Get account details by ID."""
        return self._request_model("GET", f"/execution/accounts/{account_id}", Account)

    def update_account(self, account_id: str, **kwargs: Any) -> Account:
        """Update account settings.

        Args:
            account_id: UUID of the account.
            **kwargs: Fields to update (name, risk_params, etc.).
        """
        return self._request_model(
            "PUT", f"/execution/accounts/{account_id}", Account,
            json=kwargs,
        )

    def list_positions(
        self,
        *,
        account_id: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Position]:
        """List positions with optional filters.

        Args:
            account_id: Filter by account.
            status: Filter by "open" or "closed".
            skip: Pagination offset.
            limit: Max results.
        """
        params: dict[str, Any] = {"skip": skip, "limit": limit}
        if account_id is not None:
            params["account_id"] = account_id
        if status is not None:
            params["status"] = status
        data = self._request("GET", "/execution/positions", params=params)
        if isinstance(data, list):
            return [Position.model_validate(p) for p in data]
        return [Position.model_validate(p) for p in data.get("positions", data)]

    def get_position(self, position_id: str) -> Position:
        """Get position details by ID."""
        return self._request_model("GET", f"/execution/positions/{position_id}", Position)

    def list_trades(
        self,
        *,
        account_id: str | None = None,
        asset: str | None = None,
        outcome: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Trade]:
        """List trade history with optional filters.

        Args:
            account_id: Filter by account.
            asset: Filter by asset symbol.
            outcome: Filter by "win" or "loss".
            skip: Pagination offset.
            limit: Max results.
        """
        params: dict[str, Any] = {"skip": skip, "limit": limit}
        if account_id is not None:
            params["account_id"] = account_id
        if asset is not None:
            params["asset"] = asset
        if outcome is not None:
            params["outcome"] = outcome
        data = self._request("GET", "/execution/trades", params=params)
        if isinstance(data, list):
            return [Trade.model_validate(t) for t in data]
        return [Trade.model_validate(t) for t in data.get("trades", data)]

    def evaluate(self, strategy_id: str, *, persist: bool = True) -> EvaluateResult:
        """Evaluate a strategy against current market data.

        Args:
            strategy_id: UUID of the strategy.
            persist: Whether to persist orders/positions/trades.
        """
        data = self._request("POST", f"/execution/evaluate/{strategy_id}", json={"persist": persist})
        return EvaluateResult.model_validate(data)

    def evaluate_by_object(
        self,
        strategy: dict[str, Any],
        *,
        persist: bool = False,
        open_positions: list[dict[str, Any]] | None = None,
    ) -> EvaluateResult:
        """Evaluate an inline strategy object without persisting it first.

        Useful for:
          - Testing draft strategies before saving to MangroveAI.
          - One-off evaluations against modified parameters.
          - Dry-runs with hand-tuned ``execution_state``.
          - Fully stateless ticking: pass ``open_positions`` (the value a
            previous evaluation returned) and the engine evaluates
            stop-loss / take-profit / signal / time exits against them
            with zero server-side position storage. The response's
            ``open_positions`` field carries the UPDATED set (surviving
            plus newly entered, resting bracket orders included) —
            persist it and echo it back on the next call, exactly like
            ``execution_state``.

        Args:
            strategy: Strategy dict — at minimum ``asset``, ``rules``,
                ``execution_config``, ``execution_state`` (with
                ``cash_balance`` / ``account_value`` /
                ``total_trades`` / ``num_open_positions``).
            persist: Persist orders/positions if the evaluation fires
                — defaults to False because object-based evaluation is
                typically dry-run. Not allowed together with
                ``open_positions`` (caller-owned state; the API rejects
                the combination).
            open_positions: Caller-owned open positions from the prior
                evaluation's ``open_positions`` response field.
        """
        body: dict[str, Any] = {"strategy": strategy, "persist": persist}
        if open_positions is not None:
            body["open_positions"] = open_positions
        return self._request_model(
            "POST", "/execution/evaluate",
            EvaluateResult,
            json=body,
        )

    def evaluate_bulk(
        self,
        *,
        strategy_ids: list[str] | None = None,
        strategy_configs: list[dict[str, Any]] | None = None,
        persist: bool = False,
    ) -> BulkEvaluateResult:
        """Evaluate many strategies in one call with shared market-data fetches.

        The server fetches OHLCV once per unique ``(asset, timeframe)``
        across the batch and reuses it for every strategy that needs
        it — the round-trip cost stays roughly flat with N for
        homogeneous portfolios. Per-strategy failures are captured in
        ``results[i].error`` without aborting the batch.

        Either ``strategy_ids`` (DB UUIDs) or ``strategy_configs``
        (inline dicts) — or both — must be supplied. Inline configs
        bypass the DB and require the full strategy shape
        (``asset``, ``rules``, ``execution_config``, ``execution_state``).

        Stateless positions: an inline config may carry its own
        ``open_positions`` (the list a previous evaluation returned for
        that strategy). The engine evaluates exits against them without
        server-side storage and the per-strategy result echoes the
        updated set back in its ``open_positions`` field. Not allowed
        with ``persist=True`` or a config carrying a DB id.

        Args:
            strategy_ids: UUIDs to load from the strategy table.
            strategy_configs: Inline strategy dicts to evaluate
                (optionally each carrying ``open_positions``).
            persist: Persist orders/positions per strategy.

        Raises:
            ValueError: If neither ``strategy_ids`` nor
                ``strategy_configs`` is supplied.
        """
        if not strategy_ids and not strategy_configs:
            raise ValueError(
                "Provide at least one of `strategy_ids` or `strategy_configs`"
            )
        body: dict[str, Any] = {"persist": persist}
        if strategy_ids:
            body["strategy_ids"] = strategy_ids
        if strategy_configs:
            body["strategy_configs"] = strategy_configs
        return self._request_model(
            "POST", "/execution/evaluate/bulk",
            BulkEvaluateResult,
            json=body,
        )

    def get_portfolio(self, strategy_ids: list[str]) -> PortfolioResponse:
        """Batch-read dashboard data for N strategies in one call.

        Returns name + asset + status + execution_state + open-position
        count + last 5 trades per strategy. Designed for UI cards that
        render multiple strategies — collapses the N+1 fan-out into
        one batched DB read on the server side.

        Args:
            strategy_ids: UUIDs to fetch. Max 100 per request.

        Raises:
            ValueError: If ``strategy_ids`` is empty or exceeds the
                100-ID server cap.
        """
        if not strategy_ids:
            raise ValueError("strategy_ids must be non-empty")
        if len(strategy_ids) > PORTFOLIO_MAX_IDS_PER_REQUEST:
            raise ValueError(
                f"Max {PORTFOLIO_MAX_IDS_PER_REQUEST} strategy_ids per "
                f"request, got {len(strategy_ids)}"
            )
        # Server accepts both CSV and repeated query params. CSV is
        # the more compact wire format.
        return self._request_model(
            "GET", "/execution/portfolio",
            PortfolioResponse,
            params={"strategy_ids": ",".join(strategy_ids)},
        )
