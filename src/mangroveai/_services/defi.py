from __future__ import annotations

from ..exceptions import NotImplementedLayerError
from ._base import BaseService

_MSG = "DeFi analytics endpoints are not yet available. Expected in a future SDK release."


class DeFiService(BaseService):
    """DeFi protocol analytics (Layer 3 -- not yet implemented)."""

    def get_protocol_tvl(self, protocol: str) -> None:
        raise NotImplementedLayerError(_MSG)

    def get_chain_tvl(self, chain: str) -> None:
        raise NotImplementedLayerError(_MSG)

    def get_stablecoin_metrics(self) -> None:
        raise NotImplementedLayerError(_MSG)
