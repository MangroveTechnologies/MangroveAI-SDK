"""Tests for the BacktestRequest / BulkBacktestRequest field relaxation in SDK 0.3.0.

MangroveAI #437: server-default-fillable fields are now Optional[None].
Callers can construct requests with only the strategy-specific required
fields; the server fills the rest from trading_defaults.json.
"""
from __future__ import annotations

import pytest

from mangroveai.models.backtesting import BacktestRequest, BulkBacktestRequest


class TestBacktestRequestMinimalConstruction:
    """Only asset + interval + strategy_json are required."""

    def test_minimal_construction_succeeds(self) -> None:
        req = BacktestRequest(
            asset="BTC",
            interval="1d",
            strategy_json='{"name":"t","entry":[],"exit":[]}',
        )
        # Previously-required fields are now None; server will fill.
        assert req.initial_balance is None
        assert req.min_balance_threshold is None
        assert req.min_trade_amount is None
        assert req.max_open_positions is None
        assert req.max_trades_per_day is None
        assert req.max_risk_per_trade is None
        assert req.max_units_per_trade is None
        assert req.max_trade_amount is None
        assert req.volatility_window is None
        assert req.target_volatility is None

    def test_missing_asset_still_raises(self) -> None:
        """Strategy-specific required fields still required."""
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            BacktestRequest(interval="1d", strategy_json="{}")  # type: ignore[call-arg]

    def test_missing_strategy_json_still_raises(self) -> None:
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            BacktestRequest(asset="BTC", interval="1d")  # type: ignore[call-arg]


class TestBacktestRequestBackwardsCompat:
    """Existing callers that pass the full config still work unchanged."""

    def test_fully_populated_construction_unchanged(self) -> None:
        req = BacktestRequest(
            asset="BTC",
            interval="1d",
            strategy_json='{"name":"t","entry":[],"exit":[]}',
            initial_balance=10_000,
            min_balance_threshold=0.1,
            min_trade_amount=25,
            max_open_positions=10,
            max_trades_per_day=50,
            max_risk_per_trade=0.01,
            max_units_per_trade=1_000_000,
            max_trade_amount=10_000_000,
            volatility_window=24,
            target_volatility=0.1,
        )
        assert req.initial_balance == 10_000
        assert req.max_risk_per_trade == 0.01
        assert req.target_volatility == 0.1


class TestBulkBacktestRequestMinimalConstruction:
    """Only start_date + end_date are required on bulk."""

    def test_minimal_construction_succeeds(self) -> None:
        req = BulkBacktestRequest(start_date="2026-01-01", end_date="2026-03-01")
        assert req.initial_balance is None
        assert req.max_open_positions is None
        assert req.target_volatility is None

    def test_missing_start_date_still_raises(self) -> None:
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            BulkBacktestRequest(end_date="2026-03-01")  # type: ignore[call-arg]


class TestRelaxedFieldsSerialize:
    """Model-dump honors exclude_none so None fields don't pollute the wire payload.

    This is the contract with the server: explicit values go on the wire,
    omitted values never appear, and the server backfills from its own defaults.
    """

    def test_minimal_request_serializes_without_none_defaults(self) -> None:
        req = BacktestRequest(
            asset="BTC",
            interval="1d",
            strategy_json='{"name":"t","entry":[],"exit":[]}',
        )
        payload = req.model_dump(exclude_none=True)
        # Required fields present.
        assert payload["asset"] == "BTC"
        # Relaxed fields excluded from the wire payload.
        assert "initial_balance" not in payload
        assert "max_risk_per_trade" not in payload
        assert "target_volatility" not in payload

    def test_partial_override_keeps_explicit_values(self) -> None:
        """Caller can override a subset and let the server fill the rest."""
        req = BacktestRequest(
            asset="BTC",
            interval="1d",
            strategy_json='{"name":"t","entry":[],"exit":[]}',
            initial_balance=25_000,   # explicit
            max_risk_per_trade=0.005,  # explicit; override the server default
        )
        payload = req.model_dump(exclude_none=True)
        assert payload["initial_balance"] == 25_000
        assert payload["max_risk_per_trade"] == 0.005
        # Others still omitted — server backfills.
        assert "max_open_positions" not in payload
        assert "target_volatility" not in payload
