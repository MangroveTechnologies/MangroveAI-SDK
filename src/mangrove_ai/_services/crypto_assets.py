from __future__ import annotations

from typing import Any
from urllib.parse import quote

from ..models.crypto_assets import (
    ApprovedAssetsResponse,
    CryptoAsset,
    Exchange,
    GlobalMarketResponse,
    MarketDataResponse,
    OHLCVResponse,
    SymbolExchangesResponse,
    TrendingResponse,
)
from ._base import BaseService


class CryptoAssetsService(BaseService):
    """Crypto asset data, risk scoring, and market data."""

    def list_approved_assets(self, *, top_n: int | None = None) -> ApprovedAssetsResponse:
        """Read the approved strategy universe, preserving catalogue metadata."""
        if top_n is None:
            return self._request_model("GET", "/crypto-assets/symbols", ApprovedAssetsResponse)
        return self._request_model("GET", "/crypto-assets/query", ApprovedAssetsResponse,
                                   params={"limit": top_n})

    def get_symbol_exchanges(self, symbol: str) -> SymbolExchangesResponse:
        """Read the venues that list an asset, preserving per-venue metadata."""
        return self._request_model("GET", f"/crypto-assets/symbols/{quote(symbol, safe='')}/exchanges",
                                   SymbolExchangesResponse)

    def list(
        self,
        *,
        approved_only: bool = True,
        min_score: float | None = None,
        limit: int = 100,
    ) -> list[CryptoAsset]:
        """List crypto assets with optional filters.

        Args:
            approved_only: Only return approved assets.
            min_score: Minimum overall risk score.
            limit: Max results.
        """
        params: dict[str, Any] = {"approved_only": approved_only, "limit": limit}
        if min_score is not None:
            params["min_score"] = min_score
        return self._request_list("GET", "/crypto-assets/all", CryptoAsset, params=params, key="assets")

    def get(self, symbol: str) -> CryptoAsset:
        """Get detailed asset info by symbol.

        Args:
            symbol: Asset symbol (e.g. "BTC", "ETH").
        """
        return self._request_model("GET", f"/crypto-assets/symbols/{quote(symbol, safe='')}", CryptoAsset, key="asset")

    def list_exchanges(self) -> list[Exchange]:
        """List all exchanges with tier info."""
        return self._request_list("GET", "/crypto-assets/exchanges", Exchange, key="exchanges")

    def risk_analysis(self, asset_id: str) -> dict[str, Any]:
        """Trigger risk analysis for an asset.

        Args:
            asset_id: UUID of the asset.
        """
        return self._request("POST", f"/crypto-assets/{asset_id}/risk-analysis")

    def get_ohlcv(
        self,
        symbol: str,
        *,
        days: int = 30,
        provider: str | None = None,
    ) -> OHLCVResponse:
        """Get historical OHLCV candlestick data.

        Args:
            symbol: Asset symbol (e.g. "BTC").
            days: Number of days of history.
            provider: Optional provider override; omitted uses the server's fallback chain.
        """
        params: dict[str, Any] = {"days": days}
        if provider is not None:
            params["provider"] = provider
        return self._request_model(
            "GET", f"/crypto-assets/ohlcv/{quote(symbol, safe='')}", OHLCVResponse, params=params
        )

    def get_market_data(
        self,
        symbol: str,
        *,
        provider: str | None = None,
    ) -> MarketDataResponse:
        """Get real-time market data (price, market cap, volume).

        Args:
            symbol: Asset symbol (e.g. "BTC").
            provider: Data provider override (default: coingecko).
        """
        params: dict[str, Any] = {}
        if provider is not None:
            params["provider"] = provider
        return self._request_model(
            "GET", f"/crypto-assets/market-data/{quote(symbol, safe='')}", MarketDataResponse,
            params=params if params else None,
        )

    def get_trending(self) -> TrendingResponse:
        """Get top trending crypto assets (24h search volume)."""
        return self._request_model("GET", "/crypto-assets/trending", TrendingResponse)

    def get_global_market(self) -> GlobalMarketResponse:
        """Get global crypto market statistics."""
        return self._request_model("GET", "/crypto-assets/global-market", GlobalMarketResponse)
