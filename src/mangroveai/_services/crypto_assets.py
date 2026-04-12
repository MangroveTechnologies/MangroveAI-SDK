from __future__ import annotations

from typing import Any

from ..models.crypto_assets import (
    CryptoAsset,
    Exchange,
    GlobalMarketResponse,
    MarketDataResponse,
    OHLCVResponse,
    TrendingResponse,
)
from ._base import BaseService


class CryptoAssetsService(BaseService):
    """Crypto asset data, risk scoring, and market data."""

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
        return self._request_model("GET", f"/crypto-assets/symbols/{symbol}", CryptoAsset)

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
            provider: Data provider override (default: coinapi).
        """
        params: dict[str, Any] = {"days": days}
        if provider is not None:
            params["provider"] = provider
        return self._request_model("GET", f"/crypto-assets/ohlcv/{symbol}", OHLCVResponse, params=params)

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
            "GET", f"/crypto-assets/market-data/{symbol}", MarketDataResponse,
            params=params if params else None,
        )

    def get_trending(self) -> TrendingResponse:
        """Get top trending crypto assets (24h search volume)."""
        return self._request_model("GET", "/crypto-assets/trending", TrendingResponse)

    def get_global_market(self) -> GlobalMarketResponse:
        """Get global crypto market statistics."""
        return self._request_model("GET", "/crypto-assets/global-market", GlobalMarketResponse)
