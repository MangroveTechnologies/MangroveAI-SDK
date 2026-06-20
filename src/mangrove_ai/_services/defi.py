from __future__ import annotations

from ..models.defi import (
    ChainTVLResponse,
    EtfFlowsResponse,
    LendingRatesResponse,
    PerpFundingResponse,
    ProtocolTVLResponse,
    StablecoinMetricsResponse,
    TokenUnlocksResponse,
    TreasuriesResponse,
)
from ._base import BaseService


class DeFiService(BaseService):
    """DeFi protocol analytics via DeFiLlama.

    The TVL / chain / stablecoin methods are available on any plan. The "Pro"
    methods (token unlocks, perp funding, treasuries, ETF flows, lending rates)
    require a Pro, Startup, or Enterprise plan and raise on the 403
    (``TIER_UPGRADE_REQUIRED``) returned for unentitled plans.
    """

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

    # --- Pro (require a Pro / Startup / Enterprise plan) ---------------------

    def get_token_unlocks(self) -> TokenUnlocksResponse:
        """Pro: token unlock schedules + supply metrics (supply-shock signal)."""
        return self._request_model("GET", "/defi/token-unlocks", TokenUnlocksResponse)

    def get_perp_funding(self) -> PerpFundingResponse:
        """Pro: aggregated DeFi perpetual funding rates across venues."""
        return self._request_model("GET", "/defi/perp-funding", PerpFundingResponse)

    def get_treasuries(self) -> TreasuriesResponse:
        """Pro: protocol treasury holdings (crowd-positioning signal)."""
        return self._request_model("GET", "/defi/treasuries", TreasuriesResponse)

    def get_etf_flows(self) -> EtfFlowsResponse:
        """Pro: crypto ETF net flows (institutional flow signal)."""
        return self._request_model("GET", "/defi/etf-flows", EtfFlowsResponse)

    def get_lending_borrow_rates(self) -> LendingRatesResponse:
        """Pro: lending-pool borrow rates (rate-spread features)."""
        return self._request_model("GET", "/defi/lending-rates", LendingRatesResponse)
