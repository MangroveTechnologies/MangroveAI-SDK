from __future__ import annotations

import warnings
from collections.abc import Iterator

from .._pagination import PaginatedResponse, paginate_iter
from ..models.shared import SuccessResponse
from ..models.strategies import (
    CreateStrategyRequest,
    StrategyArchiveResult,
    StrategyDetail,
    StrategyListItem,
    UpdateStrategyRequest,
)
from ._base import BaseService


class StrategiesService(BaseService):
    """Strategy CRUD and lifecycle management."""

    def list(
        self, *, skip: int = 0, limit: int = 100, include_archived: bool = False
    ) -> PaginatedResponse[StrategyListItem]:
        """List all strategies for the authenticated user.

        Args:
            skip: Pagination offset.
            limit: Max strategies per page (1-100).
            include_archived: Include archived strategies (default False). Strategies
                are never deleted; archived ones are hidden from this list by default.
        """
        data = self._request(
            "GET",
            "/strategies/",
            params={"skip": skip, "limit": limit, "include_archived": include_archived},
        )
        items = [StrategyListItem.model_validate(s) for s in data["strategies"]]
        return PaginatedResponse(
            items=items,
            total=data.get("total", len(items)),
            offset=data.get("skip", skip),
            limit=data.get("limit", limit),
        )

    def list_iter(
        self, *, limit_per_page: int = 100, include_archived: bool = False
    ) -> Iterator[StrategyListItem]:
        """Auto-paginating iterator over all strategies."""
        return paginate_iter(
            lambda offset, limit: self.list(
                skip=offset, limit=limit, include_archived=include_archived
            ),
            limit_per_page=limit_per_page,
        )

    def create(self, request: CreateStrategyRequest) -> StrategyDetail:
        """Create a new trading strategy.

        Args:
            request: Strategy definition with name, asset, entry/exit rules.
        """
        data = self._request("POST", "/strategies/", json=request.model_dump(exclude_none=True))
        return StrategyDetail.model_validate(data["strategy"])

    def get(self, strategy_id: str) -> StrategyDetail:
        """Get full strategy details by ID."""
        data = self._request("GET", f"/strategies/{strategy_id}")
        return StrategyDetail.model_validate(data["strategy"])

    def update(self, strategy_id: str, request: UpdateStrategyRequest) -> StrategyDetail:
        """Update a strategy.

        Args:
            strategy_id: UUID of the strategy.
            request: Fields to update.
        """
        data = self._request(
            "PUT", f"/strategies/{strategy_id}",
            json=request.model_dump(exclude_none=True),
        )
        return StrategyDetail.model_validate(data["strategy"])

    def archive(self, strategy_id: str) -> StrategyArchiveResult:
        """Archive a strategy, hiding it from the default list views.

        Strategies are never deleted; archiving is reversible via ``unarchive``.
        An archived strategy also stops counting toward your per-tier strategy
        limit, so this is how you free a slot when you are at your limit.
        """
        data = self._request("POST", f"/strategies/{strategy_id}/archive")
        return StrategyArchiveResult.model_validate(data)

    def unarchive(self, strategy_id: str) -> StrategyArchiveResult:
        """Unarchive a strategy, restoring it to the default list views."""
        data = self._request("POST", f"/strategies/{strategy_id}/unarchive")
        return StrategyArchiveResult.model_validate(data)

    def delete(self, strategy_id: str) -> SuccessResponse:
        """Deprecated: archive the strategy instead.

        Strategies are never hard-deleted (MangroveAI #806). This method calls the
        legacy ``DELETE /strategies/{id}`` route, which now ARCHIVES the strategy
        rather than removing it. Prefer :meth:`archive` (which needs only the
        ``strategy:update_status`` permission, not ``strategy:delete``).
        """
        warnings.warn(
            "StrategiesService.delete() is deprecated: strategies are never "
            "hard-deleted. Use archive()/unarchive() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        data = self._request("DELETE", f"/strategies/{strategy_id}")
        return SuccessResponse.model_validate(data)

    def update_status(self, strategy_id: str, status: str) -> SuccessResponse:
        """Update strategy status (draft, inactive, paper, live, archived).

        Args:
            strategy_id: UUID of the strategy.
            status: Target status.
        """
        data = self._request("PATCH", f"/strategies/{strategy_id}/status", json={"status": status})
        return SuccessResponse.model_validate(data)

    def update_execution_state(self, strategy_id: str, state: dict) -> SuccessResponse:
        """Update execution state for a strategy.

        Args:
            strategy_id: UUID of the strategy.
            state: Execution state fields to update.
        """
        data = self._request("PATCH", f"/strategies/{strategy_id}/execution-state", json=state)
        return SuccessResponse.model_validate(data)
