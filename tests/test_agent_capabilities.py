"""SDK methods for the copilot-tool capabilities exposed as public REST routes.

    client.market_data.get_market_regime        GET  /market-data/regime/{asset}
    client.market_data.classify_market_segment  GET  /market-data/segment
    client.signals.query_signal_behavior        POST /signals/behavior
    client.strategies.verify_strategy           GET  /strategies/{id}/verify
    client.config.get_execution_config_schema   GET  /config/execution-config-schema
    client.backtesting.get_benchmark            GET  /backtests/benchmark

Response fixtures are shaped like real MangroveAI responses (same keys the copilot tools
return).
"""
from __future__ import annotations

from datetime import date

import httpx
import pytest

from mangrove_ai import MangroveAI
from mangrove_ai._transport._mock import MockTransport
from mangrove_ai.exceptions import NotFoundError, ValidationError
from mangrove_ai.models.backtesting import Benchmark
from mangrove_ai.models.config import ExecutionConfigSchema
from mangrove_ai.models.market_data import MarketRegime, MarketSegment
from mangrove_ai.models.signals import SignalBehaviorResult
from mangrove_ai.models.strategies import StrategyVerification


def _client(mock: MockTransport) -> MangroveAI:
    return MangroveAI(api_key="test_abc123", environment="local", httpx_client=mock)


def _erroring_client(status: int, body: dict) -> MangroveAI:
    """A client on the real HttpTransport, so error responses go through its status mapping.

    (MockTransport returns canned responses without raising, so it cannot exercise that path.)
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)

    return MangroveAI(
        api_key="test_abc123",
        environment="local",
        auto_retry=False,
        httpx_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


REGIME = {
    "asset": "BTC",
    "bars": 365,
    "regime": {
        "asof": "2026-09-12",
        "direction": {
            "90d": {"return_pct": 8.4, "band": "bull"},
            "180d": {"return_pct": -3.1, "band": "neutral"},
            "365d": {"error": "insufficient_history", "bars": 100},
        },
        "volatility": {"vol_ann_pct": 41.3, "z_vs_baseline": -0.62, "bucket": "low"},
        "asset": "BTC",
    },
}

SEGMENT = {
    "asset": "BTC", "timeframe": "1d", "start_date": "2026-02-01", "end_date": "2026-05-01",
    "bars": 90, "duration_days": 89, "direction": "bear", "volatility": "unscored",
    "trend": "mixed", "regime_composite": "bear_unscored_mixed", "scale": None,
    "market_era": "bear-market-2",
    "scale_bands": [{"min_days": 75, "max_days": 135, "scale": "3-month"}],
    "features": {"total_return_pct": -21.4, "realized_vol_ann_pct": 48.0, "r_squared": 0.55},
}


class TestMarketRegime:
    def test_get_market_regime_types_the_reading(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/market-data/regime/BTC", json=REGIME)
        out = _client(mock).market_data.get_market_regime("BTC", lookback_days=180)

        assert isinstance(out, MarketRegime)
        assert out.bars == 365
        assert out.regime.direction["90d"].band == "bull"
        assert out.regime.direction["90d"].return_pct == 8.4
        assert out.regime.direction["365d"].error == "insufficient_history"
        assert out.regime.volatility is not None and out.regime.volatility.bucket == "low"
        assert mock.requests[-1].params == {"lookback_days": 180}

    def test_lookback_is_omitted_when_not_given(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/market-data/regime/ETH", json={**REGIME, "asset": "ETH"})
        _client(mock).market_data.get_market_regime("ETH")
        assert not mock.requests[-1].params

    def test_dump_matches_the_wire_shape(self) -> None:
        """A skill written against the copilot tool's dict reads the same keys."""
        mock = MockTransport()
        mock.add_response("GET", "/market-data/regime/BTC", json=REGIME)
        out = _client(mock).market_data.get_market_regime("BTC")
        dumped = out.model_dump(exclude_none=True)
        assert dumped["regime"]["direction"]["180d"] == {"return_pct": -3.1, "band": "neutral"}

    def test_not_found_raises(self) -> None:
        client = _erroring_client(404, {
            "error": "validation_error", "message": "could not fetch price history for FAIQ",
            "code": "RESOURCE_NOT_FOUND"})
        with pytest.raises(NotFoundError):
            client.market_data.get_market_regime("FAIQ")


class TestMarketSegment:
    def test_classify_a_date_range(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/market-data/segment", json=SEGMENT)
        out = _client(mock).market_data.classify_market_segment(
            asset="BTC", start_date="2026-02-01", end_date="2026-05-01")

        assert isinstance(out, MarketSegment)
        assert out.regime_composite == "bear_unscored_mixed"
        assert out.scale is None
        assert out.features is not None and out.features.total_return_pct == -21.4
        assert mock.requests[-1].params == {
            "asset": "BTC", "start_date": "2026-02-01", "end_date": "2026-05-01"}

    def test_classify_a_catalog_window(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/market-data/segment", json=SEGMENT)
        _client(mock).market_data.classify_market_segment(window_file="btc_1d.csv")
        assert mock.requests[-1].params == {"window_file": "btc_1d.csv"}

    def test_a_refusal_raises_validation_error(self) -> None:
        client = _erroring_client(400, {
            "error": "validation_error", "code": "INVALID_REQUEST",
            "message": "Supply window_file, or asset with start_date and end_date."})
        with pytest.raises(ValidationError):
            client.market_data.classify_market_segment(asset="BTC")


class TestSignalBehavior:
    def test_query_posts_only_the_given_arguments(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/signals/behavior", json={
            "lookup": "pick",
            "result": {"signal": "rsi_oversold", "signal_type": "FILTER", "measured": True,
                       "measured_in": "selectivity", "span": [0.0, 0.41], "matches": 2,
                       "unreachable": None,
                       "configurations": [{"params": {"window": 14, "threshold": 30},
                                           "fired_bars": 812, "is_default": True,
                                           "selectivity": 0.0921, "runs": 120,
                                           "mean_run_bars": 6.77, "longest_run_bars": 40}]},
        })
        out = _client(mock).signals.query_signal_behavior(
            "pick", signal="rsi_oversold", target_rate=0.1, max_run_bars=12, limit=5)

        assert isinstance(out, SignalBehaviorResult)
        assert out.lookup == "pick"
        assert out.result["configurations"][0]["selectivity"] == 0.0921
        assert mock.requests[-1].json == {
            "lookup": "pick", "signal_type": "FILTER", "signal": "rsi_oversold",
            "target_rate": 0.1, "max_run_bars": 12, "limit": 5}

    def test_gap_probability_for_a_trigger(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/signals/behavior", json={
            "lookup": "gap_probability", "result": {"measured": True, "configurations": []}})
        _client(mock).signals.query_signal_behavior(
            "gap_probability", signal_type="TRIGGER", signal="macd_cross",
            min_gap_range_bars=5, max_gap_range_bars=15)
        body = mock.requests[-1].json
        assert body["signal_type"] == "TRIGGER"
        assert (body["min_gap_range_bars"], body["max_gap_range_bars"]) == (5, 15)


class TestVerifyStrategy:
    def test_verify_strategy(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/strategies/s-1/verify", json={
            "found": True, "conforms": False,
            "problems": ["entry[0] signal 'rsi_oversold': no timeframe."],
            "warnings": ["exit[0] signal 'x': 'window' is at its library default (14)"],
        })
        out = _client(mock).strategies.verify_strategy("s-1")

        assert isinstance(out, StrategyVerification)
        assert out.conforms is False
        assert out.problems == ["entry[0] signal 'rsi_oversold': no timeframe."]
        assert len(out.warnings) == 1

    def test_missing_strategy_raises(self) -> None:
        client = _erroring_client(404, {
            "error": "VALIDATION_ERROR", "message": "Strategy s-2 not found",
            "code": "RESOURCE_NOT_FOUND"})
        with pytest.raises(NotFoundError):
            client.strategies.verify_strategy("s-2")


class TestExecutionConfigSchema:
    def test_get_execution_config_schema(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/config/execution-config-schema", json={
            "defaults": {"max_risk_per_trade": 0.01, "enable_volatility_adjustment": False},
            "param_glossary": {
                "max_risk_per_trade": {"status": "tunable", "description": "Fraction risked",
                                       "effect": "Higher risks more", "type": "float",
                                       "min": 0.0, "min_exclusive": True, "max": 1.0},
                "target_volatility": {"status": "gated", "description": "Target vol",
                                      "effect": "...", "gate_field": "enable_volatility_adjustment"},
            },
            "transaction_costs": {"fee_pct": 0.0085, "slippage_pct": 0.004,
                                  "source": "canon", "per_strategy": False},
            "percent_scale_note": "Percent-typed backtest metrics are returned on a 0-100 scale",
        })
        out = _client(mock).config.get_execution_config_schema()

        assert isinstance(out, ExecutionConfigSchema)
        assert out.defaults["max_risk_per_trade"] == 0.01
        entry = out.param_glossary["max_risk_per_trade"]
        assert entry.status == "tunable"
        assert entry.min == 0.0 and entry.min_exclusive is True
        assert out.param_glossary["target_volatility"].gate_field == "enable_volatility_adjustment"
        assert out.transaction_costs.per_strategy is False


class TestBenchmark:
    def test_get_benchmark_accepts_dates_or_strings(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/backtests/benchmark", json={
            "asset": "BTC", "start": "2026-01-01T00:00:00", "end": "2026-03-01T00:00:00",
            "bars": 60, "first_close": 90000.0, "last_close": 99000.0,
            "buy_and_hold_return": "10.0%", "buy_and_hold_return_raw": 10.0,
            "unit": "percent_0_100"})
        out = _client(mock).backtesting.get_benchmark("BTC", date(2026, 1, 1), "2026-03-01")

        assert isinstance(out, Benchmark)
        assert out.buy_and_hold_return == "10.0%"
        assert out.buy_and_hold_return_raw == 10.0
        assert out.unit == "percent_0_100"
        assert mock.requests[-1].params == {
            "asset": "BTC", "start_date": "2026-01-01", "end_date": "2026-03-01"}
        assert "/api/v1/backtests/benchmark" in mock.requests[-1].url
