from __future__ import annotations

from ..models.defi import ChainTVLResponse, ProtocolTVLResponse, StablecoinMetricsResponse
from ._base import BaseService


class DeFiService(BaseService):
    """DeFi protocol analytics via DeFiLlama."""

    def get_protocol_tvl(self, protocol: str) -> ProtocolTVLResponse:
        """Get total value locked for a DeFi protocol with chain breakdown.

        Args:
            protocol: Protocol name (e.g. "aave", "uniswap").
        """
        return self._request_model("GET", f"/defi/protocol/{protocol}/tvl", ProtocolTVLResponse)

    def get_chain_tvl(self, chain: str) -> ChainTVLResponse:
        """Get total value locked for a blockchain with top protocols.

        Args:
            chain: Chain name (e.g. "ethereum", "bsc", "arbitrum").
        """
        return self._request_model("GET", f"/defi/chain/{chain}/tvl", ChainTVLResponse)

    def get_stablecoin_metrics(self) -> StablecoinMetricsResponse:
        """Get global stablecoin supply and metrics by chain."""
        return self._request_model("GET", "/defi/stablecoins/metrics", StablecoinMetricsResponse)
