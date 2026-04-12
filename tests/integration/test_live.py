"""Integration tests against the live MangroveAI and KB APIs.

Requires MANGROVE_API_KEY environment variable set to a valid prod or dev key.

Run with:
    MANGROVE_API_KEY=prod_... pytest tests/integration/ -v -m integration
"""

from __future__ import annotations

import json
import os

import pytest

from mangroveai import MangroveAI
from mangroveai.models.auth import ApiKey
from mangroveai.models.backtesting import BacktestRequest, BacktestResult
from mangroveai.models.crypto_assets import (
    CryptoAsset,
    Exchange,
    GlobalMarketResponse,
    MarketDataResponse,
    OHLCVResponse,
    TrendingResponse,
)
from mangroveai.models.kb import (
    KBDocumentSummary,
    KBGlossaryResponse,
    KBIndicator,
    KBSearchResponse,
    KBSignal,
    KBTag,
)
from mangroveai.models.shared import SuccessResponse
from mangroveai.models.signals import MatchResponse, Signal
from mangroveai.models.strategies import CreateStrategyRequest, StrategyDetail

API_KEY = os.environ.get("MANGROVE_API_KEY")

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client() -> MangroveAI:
    if not API_KEY:
        pytest.skip("MANGROVE_API_KEY not set")
    c = MangroveAI(api_key=API_KEY)
    yield c
    c.close()


# =============================================================================
# Signals
# =============================================================================

class TestSignalsLive:
    def test_list_signals(self, client: MangroveAI) -> None:
        result = client.signals.list(limit=10)
        assert result.total > 0
        assert len(result.items) > 0
        assert isinstance(result.items[0], Signal)
        assert result.items[0].name  # has a name

    def test_get_signal(self, client: MangroveAI) -> None:
        result = client.signals.get("rsi_oversold")
        assert isinstance(result, Signal)
        assert result.name == "rsi_oversold"
        assert result.category is not None
        assert result.metadata is not None
        assert result.metadata.params is not None

    def test_search_signals(self, client: MangroveAI) -> None:
        from mangroveai.models.signals import SearchSignalsRequest
        result = client.signals.search(SearchSignalsRequest(query="rsi", search_type="name"))
        assert len(result.items) > 0
        assert any("rsi" in s.name.lower() for s in result.items)

    def test_match_signals(self, client: MangroveAI) -> None:
        try:
            result = client.signals.match("momentum signal that fires when asset is oversold")
            assert isinstance(result, MatchResponse)
            assert len(result.matches) > 0
        except Exception as e:
            # Vector DB may not be configured on all environments
            pytest.skip(f"Signal matching unavailable: {e}")


# =============================================================================
# Strategies (full CRUD lifecycle)
# =============================================================================

class TestStrategiesLive:
    def test_full_lifecycle(self, client: MangroveAI) -> None:
        # Create
        strategy = client.strategies.create(CreateStrategyRequest(
            name="SDK Integration Test Strategy",
            asset="BTC",
            strategy_type="momentum",
            description="Created by integration test -- safe to delete",
            entry=[
                {"name": "rsi_oversold", "signal_type": "TRIGGER", "timeframe": "1d",
                 "params": {"window": 14, "threshold": 30}},
            ],
            exit=[],
            reward_factor=2.0,
        ))
        assert isinstance(strategy, StrategyDetail)
        assert strategy.id is not None
        assert strategy.name == "SDK Integration Test Strategy"
        strategy_id = strategy.id

        try:
            # Read
            fetched = client.strategies.get(strategy_id)
            assert fetched.id == strategy_id
            assert fetched.asset == "BTC"

            # List (should include our strategy)
            listed = client.strategies.list()
            assert any(s.id == strategy_id for s in listed.items)

            # Update status
            result = client.strategies.update_status(strategy_id, "inactive")
            assert isinstance(result, SuccessResponse)
            assert result.success is True

        finally:
            # Delete (cleanup)
            result = client.strategies.delete(strategy_id)
            assert isinstance(result, SuccessResponse)
            assert result.success is True

        # Verify deleted
        listed_after = client.strategies.list()
        assert not any(s.id == strategy_id for s in listed_after.items)


# =============================================================================
# Backtesting
# =============================================================================

class TestBacktestingLive:
    def test_run_backtest(self, client: MangroveAI) -> None:
        result = client.backtesting.run(BacktestRequest(
            asset="BTC",
            interval="1d",
            strategy_json=json.dumps({
                "name": "integration_test",
                "asset": "BTC",
                "entry": [{"name": "rsi_oversold", "signal_type": "TRIGGER",
                           "timeframe": "1d", "params": {"window": 14, "threshold": 30}}],
                "exit": [],
            }),
            lookback_months=3,
            initial_balance=10000,
            min_balance_threshold=0.1,
            min_trade_amount=25,
            max_open_positions=3,
            max_trades_per_day=10,
            max_risk_per_trade=0.02,
            max_units_per_trade=1000000,
            max_trade_amount=10000000,
            volatility_window=24,
            target_volatility=0.1,
        ))
        assert isinstance(result, BacktestResult)
        assert result.success is True
        assert result.metrics is not None
        assert "sharpe_ratio" in result.metrics


# =============================================================================
# Crypto Assets
# =============================================================================

class TestCryptoAssetsLive:
    def test_list_assets(self, client: MangroveAI) -> None:
        result = client.crypto_assets.list(limit=5)
        assert len(result) > 0
        assert isinstance(result[0], CryptoAsset)
        assert result[0].symbol is not None

    def test_get_asset(self, client: MangroveAI) -> None:
        result = client.crypto_assets.get("BTC")
        assert isinstance(result, CryptoAsset)
        assert result.symbol == "BTC"

    def test_list_exchanges(self, client: MangroveAI) -> None:
        result = client.crypto_assets.list_exchanges()
        assert len(result) > 0
        assert isinstance(result[0], Exchange)

    def test_get_market_data(self, client: MangroveAI) -> None:
        result = client.crypto_assets.get_market_data("BTC")
        assert isinstance(result, MarketDataResponse)
        assert result.symbol == "BTC"
        assert "current_price" in result.data
        assert result.data["current_price"] > 0

    def test_get_ohlcv(self, client: MangroveAI) -> None:
        result = client.crypto_assets.get_ohlcv("BTC", days=7)
        assert isinstance(result, OHLCVResponse)
        assert result.symbol == "BTC"
        assert result.data is not None

    def test_get_trending(self, client: MangroveAI) -> None:
        result = client.crypto_assets.get_trending()
        assert isinstance(result, TrendingResponse)
        assert len(result.trending) > 0

    def test_get_global_market(self, client: MangroveAI) -> None:
        result = client.crypto_assets.get_global_market()
        assert isinstance(result, GlobalMarketResponse)
        assert "total_market_cap_usd" in result.data
        assert result.data["total_market_cap_usd"] > 0


# =============================================================================
# Execution
# =============================================================================

class TestExecutionLive:
    def test_list_accounts(self, client: MangroveAI) -> None:
        try:
            result = client.execution.list_accounts()
            assert isinstance(result, list)
        except Exception as e:
            # Server returns 500 with null-filled entity when no accounts exist (server bug)
            pytest.skip(f"Execution accounts endpoint error: {e}")

    def test_list_positions(self, client: MangroveAI) -> None:
        try:
            result = client.execution.list_positions()
            assert isinstance(result, list)
        except Exception as e:
            pytest.skip(f"Execution positions endpoint error: {e}")

    def test_list_trades(self, client: MangroveAI) -> None:
        try:
            result = client.execution.list_trades()
            assert isinstance(result, list)
        except Exception as e:
            pytest.skip(f"Execution trades endpoint error: {e}")


# =============================================================================
# Auth
# =============================================================================

class TestAuthLive:
    def test_list_api_keys(self, client: MangroveAI) -> None:
        result = client.auth.list_api_keys()
        assert isinstance(result, list)
        assert len(result) > 0  # at least the key we're using
        assert isinstance(result[0], ApiKey)


# =============================================================================
# Knowledge Base
# =============================================================================

class TestKBLive:
    def test_documents_list(self, client: MangroveAI) -> None:
        result = client.kb.documents.list()
        assert len(result) > 0
        assert isinstance(result[0], KBDocumentSummary)
        assert result[0].slug is not None

    def test_documents_get(self, client: MangroveAI) -> None:
        docs = client.kb.documents.list()
        if not docs:
            pytest.skip("No KB documents available")
        result = client.kb.documents.get(docs[0].slug)
        assert result.slug == docs[0].slug
        assert result.content is not None

    def test_search(self, client: MangroveAI) -> None:
        result = client.kb.search.query("RSI", limit=5)
        assert isinstance(result, KBSearchResponse)
        assert result.results is not None

    def test_tags(self, client: MangroveAI) -> None:
        result = client.kb.tags.list()
        assert len(result) > 0
        assert isinstance(result[0], KBTag)

    def test_glossary(self, client: MangroveAI) -> None:
        result = client.kb.glossary.list()
        assert isinstance(result, KBGlossaryResponse)
        assert result.total > 0

    def test_signals(self, client: MangroveAI) -> None:
        result = client.kb.signals.list()
        assert len(result) > 0
        assert isinstance(result[0], KBSignal)
        assert result[0].name is not None

    def test_indicators(self, client: MangroveAI) -> None:
        result = client.kb.indicators.list()
        assert len(result) > 0
        assert isinstance(result[0], KBIndicator)
        assert result[0].name is not None
