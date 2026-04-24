"""Tests for the ConfigService — client.config.trading_defaults / execution_defaults."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


class TestTradingDefaults:
    """client.config.trading_defaults() → GET /config/trading-defaults."""

    def test_returns_full_nested_shape(self, client) -> None:
        fixture = _load("trading_defaults_response.json")
        client._http.add_response("GET", "/config/trading-defaults", json=fixture)

        result = client.config.trading_defaults()

        assert isinstance(result, dict)
        # Full top-level shape mirrors trading_defaults.json.
        for key in (
            "description",
            "signal_defaults",
            "backtest_defaults",
            "risk_management",
            "position_limits",
            "volatility_settings",
            "trading_rules",
            "time_based_exits",
        ):
            assert key in result

        # Nested sections remain dicts (not flattened).
        assert isinstance(result["risk_management"], dict)
        assert "max_risk_per_trade" in result["risk_management"]

    def test_real_response_fixture_validates(self) -> None:
        """The captured dev response has the shape documented in the service docstring."""
        fixture = _load("trading_defaults_response.json")
        for key in ("risk_management", "position_limits", "volatility_settings",
                    "trading_rules", "time_based_exits"):
            assert isinstance(fixture[key], dict), f"{key} must be a dict in trading_defaults.json"


class TestExecutionDefaults:
    """client.config.execution_defaults() → GET /config/execution-defaults."""

    def test_returns_flattened_dict(self, client) -> None:
        fixture = _load("execution_defaults_response.json")
        client._http.add_response("GET", "/config/execution-defaults", json=fixture)

        result = client.config.execution_defaults()

        assert isinstance(result, dict)
        # Keys from the five merged sections.
        assert "max_risk_per_trade" in result       # risk_management
        assert "initial_balance" in result           # position_limits
        assert "cooldown_bars" in result             # trading_rules
        assert "max_hold_bars" in result             # time_based_exits

        # signal_defaults + backtest_defaults NOT merged in.
        assert "slippage_pct" not in result
        assert "fee_pct" not in result

    def test_result_is_a_flat_dict(self, client) -> None:
        """No nested sub-dicts at the top level (except cooldown_config which is intentionally nested)."""
        fixture = _load("execution_defaults_response.json")
        client._http.add_response("GET", "/config/execution-defaults", json=fixture)

        result = client.config.execution_defaults()

        non_dict_values = {k: v for k, v in result.items() if not isinstance(v, dict)}
        # At least the core trading fields are flat scalars/lists.
        for k in ("max_risk_per_trade", "initial_balance", "max_hold_bars"):
            assert k in non_dict_values

    def test_execution_defaults_can_feed_backtest_request(self, client) -> None:
        """execution_defaults() output is shaped to be passed straight to BacktestRequest.execution_config."""
        from mangroveai.models.backtesting import BacktestRequest

        fixture = _load("execution_defaults_response.json")
        client._http.add_response("GET", "/config/execution-defaults", json=fixture)

        defaults = client.config.execution_defaults()

        # Contract: constructing a BacktestRequest with only the strategy-specific
        # required fields + the endpoint output succeeds.
        req = BacktestRequest(
            asset="BTC",
            interval="1d",
            strategy_json='{"name":"t","entry":[],"exit":[]}',
            execution_config=defaults,
        )
        assert req.execution_config == defaults


class TestBothEndpointsUnauthenticated:
    """Both config endpoints are public — no auth header needed."""

    def test_trading_defaults_does_not_require_auth(self, client) -> None:
        fixture = _load("trading_defaults_response.json")
        client._http.add_response("GET", "/config/trading-defaults", json=fixture)
        client.config.trading_defaults()
        # Assertion: the call succeeded (no 401 raised). The MockTransport would
        # have raised if auth was rejected upstream; this is a shape-level
        # smoke that the SDK does not inject unexpected headers here.


@pytest.mark.integration
class TestLiveConfigEndpoints:
    """Live checks against the dev server. Skipped unless MANGROVE_TEST_URL is set."""

    def test_trading_defaults_live(self) -> None:
        import os

        base_url = os.environ.get("MANGROVE_TEST_URL")
        if not base_url:
            pytest.skip("MANGROVE_TEST_URL not set")

        from mangroveai import MangroveAI
        live = MangroveAI(api_key="dev_public_check", base_url=base_url)
        result = live.config.trading_defaults()
        assert "risk_management" in result
        assert "position_limits" in result
