from __future__ import annotations

from ..exceptions import NotImplementedLayerError
from ._base import BaseService

_MSG = "On-chain analytics endpoints are not yet available. Expected in a future SDK release."


class OnChainService(BaseService):
    """On-chain analytics (Layer 3 -- not yet implemented)."""

    def get_smart_money_sentiment(self, symbol: str, *, chain: str | None = None) -> None:
        raise NotImplementedLayerError(_MSG)

    def screen_smart_money(self, *, chains: list[str] | None = None, timeframe: str = "24h", limit: int = 20) -> None:
        raise NotImplementedLayerError(_MSG)

    def get_token_holders(self, symbol: str) -> None:
        raise NotImplementedLayerError(_MSG)

    def get_whale_transactions(
        self, *, symbol: str | None = None, min_value: float = 500_000, hours_back: int = 24,
    ) -> None:
        raise NotImplementedLayerError(_MSG)

    def get_exchange_flows(self, *, symbol: str | None = None, hours_back: int = 24) -> None:
        raise NotImplementedLayerError(_MSG)

    def get_whale_activity(self, symbol: str, *, hours_back: int = 24) -> None:
        raise NotImplementedLayerError(_MSG)
