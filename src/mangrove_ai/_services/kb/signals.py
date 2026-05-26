from __future__ import annotations

from ...models.kb import KBSignal
from .._base import BaseService


class KBSignalsService(BaseService):
    """KB signal metadata."""

    def list(self, *, category: str | None = None, signal_type: str | None = None) -> list[KBSignal]:
        """List all signals with optional filters.

        Args:
            category: Filter by category (Momentum, Trend, Volume, Volatility, Patterns).
            signal_type: Filter by type (TRIGGER or FILTER).
        """
        params = {}
        if category is not None:
            params["category"] = category
        if signal_type is not None:
            params["signal_type"] = signal_type
        data = self._request("GET", "/signals", params=params or None)
        return [KBSignal.model_validate(s) for s in data["signals"]]

    def get(self, name: str) -> KBSignal:
        """Get full metadata for a signal by name."""
        return self._request_model("GET", f"/signals/{name}", KBSignal)
