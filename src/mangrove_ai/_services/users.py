from __future__ import annotations

from typing import Any

from .._pagination import PaginatedResponse
from ..models.users import UserBacktest, UserMetrics, UserStrategy
from ._base import BaseService


class UsersService(BaseService):
    """Authenticated-user data: usage metrics, strategies, and backtests.

    Wraps the ``GET /users/me/*`` endpoints. The caller is always the API
    key's own user -- there is no cross-user access.
    """

    def get_my_metrics(self) -> UserMetrics:
        """Usage metrics for the authenticated user.

        Conversations, messages, estimated token usage (with a per-category
        breakdown), strategy/backtest counts, and tool-call counts.
        """
        return self._request_model("GET", "/users/me/metrics", UserMetrics, key="metrics")

    def get_my_strategies(
        self,
        *,
        search: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        include_archived: bool = False,
    ) -> PaginatedResponse[UserStrategy]:
        """List the authenticated user's strategies.

        Args:
            search: Filter by name or asset.
            status: Filter by status (e.g. ``"active"`` / ``"inactive"``).
            limit: Page size (default 50).
            offset: Page offset (default 0).
            include_archived: Include archived strategies (hidden by default;
                strategies are never hard-deleted).
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if search is not None:
            params["search"] = search
        if status is not None:
            params["status"] = status
        if include_archived:
            params["include_archived"] = "true"
        data = self._request("GET", "/users/me/strategies", params=params)
        items = [UserStrategy.model_validate(s) for s in data.get("strategies", [])]
        return PaginatedResponse(
            items=items, total=data.get("total", len(items)), offset=offset, limit=limit
        )

    def get_my_backtests(
        self,
        *,
        status: str | None = None,
        asset: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
        offset: int = 0,
        include_archived: bool = False,
        session_id: str | None = None,
    ) -> PaginatedResponse[UserBacktest]:
        """List the authenticated user's backtests (archived hidden by default).

        Each row carries a ``result`` verdict (PASS / FAIL / INSUFFICIENT_TRADES,
        or the raw status for non-completed runs).
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        for name, value in (
            ("status", status),
            ("asset", asset),
            ("date_from", date_from),
            ("date_to", date_to),
            ("session_id", session_id),
        ):
            if value is not None:
                params[name] = value
        if include_archived:
            params["include_archived"] = "true"
        data = self._request("GET", "/users/me/backtests", params=params)
        items = [UserBacktest.model_validate(b) for b in data.get("backtests", [])]
        return PaginatedResponse(
            items=items, total=data.get("total", len(items)), offset=offset, limit=limit
        )
