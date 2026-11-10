from __future__ import annotations

from typing import Literal
from urllib.parse import quote

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
        return self._request_model("GET", f"/defi/protocol/{quote(protocol, safe='')}/tvl", ProtocolTVLResponse)

    def get_chain_tvl(self, chain: str) -> ChainTVLResponse:
        """Get total value locked for a blockchain with top protocols.

        Args:
            chain: Chain name (e.g. "ethereum", "bsc", "arbitrum").
        """
        return self._request_model("GET", f"/defi/chain/{quote(chain, safe='')}/tvl", ChainTVLResponse)

    def get_stablecoin_metrics(self) -> StablecoinMetricsResponse:
        """Get global stablecoin supply and metrics by chain."""
        return self._request_model("GET", "/defi/stablecoins/metrics", StablecoinMetricsResponse)

    # --- Pro (require a Pro / Startup / Enterprise plan) ---------------------

    def get_token_unlocks(
        self, *, symbol: str | None = None, protocol: str | None = None,
        days_ahead: int = 30, rank_by: Literal["next_unlock", "cliff_value_usd"] = "next_unlock",
        limit: int = 25, offset: int = 0,
    ) -> TokenUnlocksResponse:
        """Pro: one page of token unlocks within ``days_ahead`` (1-365).

        Symbol/protocol are exact case-insensitive filters. A matched token is
        returned even if its next unlock is outside the window. Rank by soonest
        unlock or largest cliff USD value. Page size is 1-100; continue with the
        returned ``next_offset``. Each page is a separate request.
        """
        return self._request_model("GET", "/defi/token-unlocks", TokenUnlocksResponse,
                                   params=_params(symbol=symbol, protocol=protocol, days_ahead=days_ahead,
                                                  rank_by=rank_by, limit=limit, offset=offset))

    def get_perp_funding(
        self, *, symbol: str | None = None, venue: str | None = None,
        limit: int = 25, offset: int = 0,
    ) -> PerpFundingResponse:
        """Pro: funding by venue/market, largest open interest first.

        Filter by base symbol and/or venue. Limit is 1-100; continue using the
        response's ``next_offset``, not the number of rows requested.
        """
        return self._request_model("GET", "/defi/perp-funding", PerpFundingResponse,
                                   params=_params(symbol=symbol, venue=venue, limit=limit, offset=offset))

    def get_treasuries(
        self, *, symbol: str | None = None, protocol: str | None = None,
        limit: int = 25, offset: int = 0,
    ) -> TreasuriesResponse:
        """Pro: filtered treasury holdings. Limit 1-100; page with ``next_offset``."""
        return self._request_model("GET", "/defi/treasuries", TreasuriesResponse,
                                   params=_params(symbol=symbol, protocol=protocol, limit=limit, offset=offset))

    def get_etf_flows(
        self, *, symbol: str | None = None, lookback_days: int = 30,
        limit: int = 25, offset: int = 0,
    ) -> EtfFlowsResponse:
        """Pro: daily ETF flows and complete window totals, optionally by symbol.

        Limit is 1-100; use ``next_offset`` to read the next page of daily rows.
        """
        return self._request_model("GET", "/defi/etf-flows", EtfFlowsResponse,
                                   params=_params(symbol=symbol, lookback_days=lookback_days,
                                                  limit=limit, offset=offset))

    def get_lending_borrow_rates(
        self, *, symbol: str | None = None, protocol: str | None = None,
        chain: str | None = None, min_tvl_usd: float | None = None,
        limit: int = 25, offset: int = 0,
    ) -> LendingRatesResponse:
        """Pro: pool rates filtered by symbol, protocol, chain and minimum TVL.

        Limit is 1-100; use ``next_offset`` to continue through matching pools.
        """
        return self._request_model("GET", "/defi/lending-rates", LendingRatesResponse,
                                   params=_params(symbol=symbol, protocol=protocol, chain=chain,
                                                  min_tvl_usd=min_tvl_usd, limit=limit, offset=offset))

    def get_perp_funding_rates(
        self, *, symbol: str | None = None, venue: str | None = None,
        limit: int = 25, offset: int = 0,
    ) -> PerpFundingResponse:
        """Canonical-name alias for perpetual funding rates."""
        return self.get_perp_funding(symbol=symbol, venue=venue, limit=limit, offset=offset)

    def get_lending_rates(
        self, *, symbol: str | None = None, protocol: str | None = None,
        chain: str | None = None, min_tvl_usd: float | None = None,
        limit: int = 25, offset: int = 0,
    ) -> LendingRatesResponse:
        """Canonical-name alias for lending and borrow rates."""
        return self.get_lending_borrow_rates(symbol=symbol, protocol=protocol, chain=chain,
                                             min_tvl_usd=min_tvl_usd, limit=limit, offset=offset)


def _params(**values: str | int | float | None) -> dict[str, str | int | float]:
    """Omit absent filters; preserve explicit zero values for bounds and offsets."""
    return {name: value for name, value in values.items() if value is not None}
