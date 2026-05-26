from __future__ import annotations

from ...models.kb import KBIndicator
from .._base import BaseService


class KBIndicatorsService(BaseService):
    """KB indicator metadata."""

    def list(self, *, category: str | None = None) -> list[KBIndicator]:
        """List all indicators with optional category filter.

        Args:
            category: Filter by category (Momentum, Trend, Volume, Volatility, Patterns, Returns).
        """
        params = {}
        if category is not None:
            params["category"] = category
        data = self._request("GET", "/indicators", params=params or None)
        return [KBIndicator.model_validate(i) for i in data["indicators"]]

    def get(self, name: str) -> KBIndicator:
        """Get full spec for an indicator by name."""
        return self._request_model("GET", f"/indicators/{name}", KBIndicator)
