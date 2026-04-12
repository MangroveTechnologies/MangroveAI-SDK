from __future__ import annotations

from typing import Any

from ..models.execution import (
    Account,
    CreateAccountRequest,
    EvaluateResult,
    Position,
    Trade,
)
from ._base import BaseService


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
        return self._request_list("GET", "/execution/accounts", Account, params=params or None, key="accounts")

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
