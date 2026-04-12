from __future__ import annotations

from mangroveai import MangroveAI
from mangroveai._transport._mock import MockTransport
from mangroveai.models.crypto_assets import (
    CryptoAsset,
    Exchange,
    MarketDataResponse,
    OHLCVResponse,
    TrendingResponse,
    GlobalMarketResponse,
)


def _make_client(mock: MockTransport) -> MangroveAI:
    return MangroveAI(api_key="test_abc123", environment="local", httpx_client=mock)


ASSET_JSON = {
    "id": "asset-uuid-1",
    "symbol": "BTC",
    "name": "Bitcoin",
    "risk_scores": {
        "market_cap": 95,
        "liquidity": 90,
        "exchange": 92,
        "age": 100,
        "volatility": 45,
        "supply_distribution": 70,
        "price_stability": 55,
        "overall": 78.1,
    },
    "is_approved": True,
    "regulatory_status": "approved",
    "security_status": "secure",
    "metadata": {
        "market_cap": 1800000000000,
        "volume_24h": 30000000000,
        "age_days": 5500,
        "exchanges": ["binance", "coinbase", "kraken"],
    },
    "timestamps": {
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-04-01T00:00:00Z",
        "last_evaluated_at": "2026-04-10T00:00:00Z",
    },
}


class TestCryptoAssetsList:
    def test_list_returns_assets(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/crypto-assets/all", json={
            "success": True,
            "assets": [ASSET_JSON],
            "count": 1,
        })
        client = _make_client(mock)

        result = client.crypto_assets.list()

        assert len(result) == 1
        assert isinstance(result[0], CryptoAsset)
        assert result[0].symbol == "BTC"
        assert result[0].risk_scores.overall == 78.1
        assert result[0].metadata.exchanges == ["binance", "coinbase", "kraken"]

    def test_list_with_filters(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/crypto-assets/all", json={
            "success": True,
            "assets": [],
            "count": 0,
        })
        client = _make_client(mock)

        client.crypto_assets.list(approved_only=True, min_score=80, limit=50)

        params = mock.requests[0].params
        assert params["approved_only"] is True
        assert params["min_score"] == 80
        assert params["limit"] == 50


class TestCryptoAssetsGet:
    def test_get_returns_asset(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/crypto-assets/symbols/BTC", json=ASSET_JSON)
        client = _make_client(mock)

        result = client.crypto_assets.get("BTC")

        assert isinstance(result, CryptoAsset)
        assert result.symbol == "BTC"
        assert result.is_approved is True
        assert result.timestamps.last_evaluated_at == "2026-04-10T00:00:00Z"


class TestCryptoAssetsExchanges:
    def test_list_exchanges(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/crypto-assets/exchanges", json={
            "success": True,
            "exchanges": [
                {"id": "ex-1", "name": "binance", "display_name": "Binance", "tier": 1, "is_active": True},
                {"id": "ex-2", "name": "kraken", "display_name": "Kraken", "tier": 1, "is_active": True},
            ],
            "count": 2,
        })
        client = _make_client(mock)

        result = client.crypto_assets.list_exchanges()

        assert len(result) == 2
        assert isinstance(result[0], Exchange)
        assert result[0].tier == 1


class TestCryptoAssetsRiskAnalysis:
    def test_risk_analysis_returns_dict(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/crypto-assets/asset-uuid-1/risk-analysis", json={
            "success": True,
            "risk_scores": {"overall": 82.5},
            "status": "completed",
        })
        client = _make_client(mock)

        result = client.crypto_assets.risk_analysis("asset-uuid-1")

        assert result["success"] is True
        assert result["risk_scores"]["overall"] == 82.5


class TestCryptoAssetsOHLCV:
    def test_get_ohlcv(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/crypto-assets/ohlcv/ETH", json={
            "success": True,
            "symbol": "ETH",
            "data_points": 30,
            "data": [
                {"timestamp": "2026-03-12T00:00:00Z", "open": 3200, "high": 3250, "low": 3150, "close": 3240, "volume": 850000},
            ],
        })
        client = _make_client(mock)

        result = client.crypto_assets.get_ohlcv("ETH", days=30)

        assert isinstance(result, OHLCVResponse)
        assert result.symbol == "ETH"
        assert result.data_points == 30
        assert len(result.data) == 1

    def test_get_ohlcv_with_provider(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/crypto-assets/ohlcv/BTC", json={
            "success": True,
            "symbol": "BTC",
            "data_points": 7,
            "data": [],
        })
        client = _make_client(mock)

        client.crypto_assets.get_ohlcv("BTC", days=7, provider="coingecko")

        assert mock.requests[0].params["provider"] == "coingecko"
        assert mock.requests[0].params["days"] == 7


class TestCryptoAssetsMarketData:
    def test_get_market_data(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/crypto-assets/market-data/BTC", json={
            "success": True,
            "symbol": "BTC",
            "data": {
                "current_price": 91282.00,
                "market_cap": 1823027068010,
                "volume_24h": 30539603461,
                "price_change_24h_pct": 2.3,
            },
        })
        client = _make_client(mock)

        result = client.crypto_assets.get_market_data("BTC")

        assert isinstance(result, MarketDataResponse)
        assert result.data["current_price"] == 91282.00
        assert result.data["market_cap"] == 1823027068010


class TestCryptoAssetsTrending:
    def test_get_trending(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/crypto-assets/trending", json={
            "success": True,
            "count": 2,
            "trending": [
                {"symbol": "PEPE", "rank": 1},
                {"symbol": "WIF", "rank": 2},
            ],
        })
        client = _make_client(mock)

        result = client.crypto_assets.get_trending()

        assert isinstance(result, TrendingResponse)
        assert result.count == 2
        assert len(result.trending) == 2


class TestCryptoAssetsGlobalMarket:
    def test_get_global_market(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/crypto-assets/global-market", json={
            "success": True,
            "data": {
                "total_market_cap_usd": 3200000000000,
                "btc_dominance": 54.2,
                "eth_dominance": 16.8,
                "market_cap_change_24h_pct": 1.5,
            },
        })
        client = _make_client(mock)

        result = client.crypto_assets.get_global_market()

        assert isinstance(result, GlobalMarketResponse)
        assert result.data["btc_dominance"] == 54.2
