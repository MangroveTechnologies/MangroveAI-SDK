from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .._pagination import PaginatedResponse, paginate_iter
from ..models.signals import (
    EvaluateResponse,
    MatchResponse,
    SearchSignalsRequest,
    Signal,
    ValidationResponse,
)
from ._base import BaseService


class SignalsService(BaseService):
    """Signal discovery, evaluation, and validation."""

    def list(self, *, limit: int = 50, offset: int = 0) -> PaginatedResponse[Signal]:
        """List all available trading signals.

        Args:
            limit: Max signals per page (1-100).
            offset: Pagination offset.
        """
        data = self._request("GET", "/signals/", params={"limit": limit, "offset": offset})
        items = [Signal.model_validate(s) for s in data["signals"]]
        return PaginatedResponse(
            items=items,
            total=data.get("total", len(items)),
            offset=data.get("offset", offset),
            limit=data.get("limit", limit),
        )

    def list_iter(self, *, limit_per_page: int = 50) -> Iterator[Signal]:
        """Auto-paginating iterator over all signals."""
        return paginate_iter(
            lambda offset, limit: self.list(limit=limit, offset=offset),
            limit_per_page=limit_per_page,
        )

    def get(self, signal_name: str) -> Signal:
        """Get full metadata for a signal by name."""
        data = self._request("GET", f"/signals/{signal_name}")
        return Signal.model_validate(data)

    def search(self, request: SearchSignalsRequest) -> PaginatedResponse[Signal]:
        """Search signals by name, params, or keywords.

        Args:
            request: Search query with search_type (name, params, keywords).
        """
        data = self._request("POST", "/signals/search", json=request.model_dump())
        items = [Signal.model_validate(s) for s in data["signals"]]
        return PaginatedResponse(
            items=items,
            total=data.get("total", len(items)),
            offset=data.get("offset", request.offset),
            limit=data.get("limit", request.limit),
        )

    def match(
        self,
        description: str,
        *,
        top_k: int = 5,
        similarity_threshold: float = 0.5,
    ) -> MatchResponse:
        """Find signals matching a natural language description.

        Args:
            description: What the signal should do.
            top_k: Max number of matches to return.
            similarity_threshold: Minimum similarity score (0-1).
        """
        data = self._request("POST", "/signals/match", json={
            "description": description,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
        })
        return MatchResponse.model_validate(data)

    def evaluate(
        self,
        signal_name: str,
        market_data: list[dict[str, Any]],
        parameters: dict[str, Any],
    ) -> EvaluateResponse:
        """Evaluate a signal against market data.

        Args:
            signal_name: Signal function name.
            market_data: OHLCV data points.
            parameters: Signal-specific parameters.
        """
        data = self._request("POST", f"/signals/{signal_name}/evaluate", json={
            "market_data": market_data,
            "parameters": parameters,
        })
        return EvaluateResponse.model_validate(data)

    def validate(
        self,
        code: str,
        params: dict[str, Any],
        description: str,
    ) -> ValidationResponse:
        """Validate signal code, parameters, and metadata.

        Args:
            code: Python function code for the signal.
            params: Parameter specifications.
            description: Signal description.
        """
        data = self._request("POST", "/signals/validate", json={
            "code": code,
            "params": params,
            "description": description,
        })
        return ValidationResponse.model_validate(data)
