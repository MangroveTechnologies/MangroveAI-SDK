from __future__ import annotations

import json
import warnings

from mangrove_ai._services._backtest_payload import backtest_payload
from mangrove_ai.models.backtesting import BacktestRequest, BulkBacktestRequest

# ---------------------------------------------------------------------------
# Minimal required kwargs shared across all BacktestRequest constructions
# ---------------------------------------------------------------------------
_BASE_BACKTEST = dict(
    asset="BTC",
    interval="1h",
    strategy_json='{"name":"test","entry":[],"exit":[]}',
    initial_balance=10000,
    min_balance_threshold=0.1,
    min_trade_amount=25,
    max_open_positions=3,
    max_trades_per_day=10,
    max_risk_per_trade=0.02,
    max_units_per_trade=1_000_000,
    max_trade_amount=10_000_000,
    volatility_window=24,
    target_volatility=0.1,
)

_BASE_BULK = dict(
    start_date="2025-01-01",
    end_date="2025-06-01",
    initial_balance=10000,
    min_balance_threshold=0.1,
    min_trade_amount=25,
    max_open_positions=3,
    max_trades_per_day=10,
    max_risk_per_trade=0.02,
    max_units_per_trade=1_000_000,
    max_trade_amount=10_000_000,
    volatility_window=24,
    target_volatility=0.1,
)

_MINIMAL_COOLDOWN_CONFIG: dict[str, dict] = {
    "1h": {
        "max_hold_time_hours": 24,
        "short_loss_limit": 4,
        "long_loss_limit": 6,
        "short_window_bars": 48,
        "long_window_bars": 144,
    }
}


class TestCooldownConfigField:
    """cooldown_config validates cleanly and round-trips through JSON."""

    def test_backtest_request_accepts_cooldown_config(self) -> None:
        req = BacktestRequest(**_BASE_BACKTEST, cooldown_config=_MINIMAL_COOLDOWN_CONFIG)
        assert req.cooldown_config is not None
        assert req.cooldown_config["1h"]["short_loss_limit"] == 4

    def test_bulk_backtest_request_accepts_cooldown_config(self) -> None:
        req = BulkBacktestRequest(**_BASE_BULK, cooldown_config=_MINIMAL_COOLDOWN_CONFIG)
        assert req.cooldown_config is not None
        assert req.cooldown_config["1h"]["long_window_bars"] == 144

    def test_cooldown_config_none_by_default(self) -> None:
        req = BacktestRequest(**_BASE_BACKTEST)
        assert req.cooldown_config is None

    def test_multiple_timeframes(self) -> None:
        config = {
            "5m": {
                "max_hold_time_hours": 96,
                "short_loss_limit": 4,
                "long_loss_limit": 6,
                "short_window_bars": 180,
                "long_window_bars": 480,
            },
            "1h": {
                "max_hold_time_hours": 24,
                "short_loss_limit": 4,
                "long_loss_limit": 6,
                "short_window_bars": 48,
                "long_window_bars": 144,
            },
        }
        req = BacktestRequest(**_BASE_BACKTEST, cooldown_config=config)
        assert set(req.cooldown_config.keys()) == {"5m", "1h"}  # type: ignore[union-attr]


class TestBarsOnlyScalars:
    """The three legacy scalars are sent only when a caller sets them (cooldown_model='bars')."""

    _FIELDS = ("cooldown_bars", "daily_momentum_limit", "weekly_momentum_limit")

    def test_defaults_are_unset_and_do_not_warn(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            single = BacktestRequest(**_BASE_BACKTEST)
            bulk = BulkBacktestRequest(**_BASE_BULK)
        assert not [w for w in caught if issubclass(w.category, DeprecationWarning)]
        for request in (single, bulk):
            for field in self._FIELDS:
                assert getattr(request, field) is None

    def test_unset_scalars_are_omitted_from_the_payload(self) -> None:
        for request in (BacktestRequest(**_BASE_BACKTEST), BulkBacktestRequest(**_BASE_BULK)):
            payload = backtest_payload(request)
            assert not set(self._FIELDS) & set(payload)

    def test_set_scalars_are_sent_for_the_bars_model(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            single = BacktestRequest(
                **_BASE_BACKTEST, cooldown_model="bars", cooldown_bars=48,
                daily_momentum_limit=5.0, weekly_momentum_limit=4.0)
            bulk = BulkBacktestRequest(**_BASE_BULK, cooldown_bars=12, daily_momentum_limit=2.0)
        payload = backtest_payload(single)
        assert (payload["cooldown_bars"], payload["daily_momentum_limit"], payload["weekly_momentum_limit"]) == (48, 5.0, 4.0)
        payload = backtest_payload(bulk)
        assert (payload["cooldown_bars"], payload["daily_momentum_limit"]) == (12, 2.0)
        assert "weekly_momentum_limit" not in payload


class TestDeprecationWarnings:
    """Old top-level fields emit DeprecationWarning at construction time."""

    def test_cooldown_bars_warns(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            BacktestRequest(**_BASE_BACKTEST, cooldown_bars=48)
        messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
        assert any("field 'cooldown_bars'" in m for m in messages)

    def test_daily_momentum_limit_warns(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            BacktestRequest(**_BASE_BACKTEST, daily_momentum_limit=5.0)
        messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
        assert any("field 'daily_momentum_limit'" in m for m in messages)

    def test_weekly_momentum_limit_warns(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            BacktestRequest(**_BASE_BACKTEST, weekly_momentum_limit=5.0)
        messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
        assert any("field 'weekly_momentum_limit'" in m for m in messages)

    def test_max_hold_time_hours_warns(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            BacktestRequest(**_BASE_BACKTEST, max_hold_time_hours=48.0)
        messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
        assert any("field 'max_hold_time_hours'" in m for m in messages)

    def test_bulk_request_deprecated_fields_warn(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            BulkBacktestRequest(**_BASE_BULK, cooldown_bars=12, daily_momentum_limit=2.0)
        messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
        assert any("field 'cooldown_bars'" in m for m in messages)
        assert any("field 'daily_momentum_limit'" in m for m in messages)

    def test_max_hold_time_hours_none_does_not_warn(self) -> None:
        # When max_hold_time_hours is not explicitly set (defaults to None), no deprecation warning
        # should be emitted for that specific field. The message starts with
        # "The top-level field 'max_hold_time_hours'" when it fires.
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            req = BacktestRequest(**_BASE_BACKTEST)
        dep_msgs = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
        # Only the specific field-named warning indicates max_hold_time_hours fired.
        assert not any("field 'max_hold_time_hours'" in m for m in dep_msgs)
        assert req.max_hold_time_hours is None


class TestOldAndNewFieldsTogether:
    """Both old and new fields accepted simultaneously (no mutual exclusion)."""

    def test_backtest_old_and_new_no_error(self) -> None:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            req = BacktestRequest(
                **_BASE_BACKTEST,
                cooldown_bars=48,
                daily_momentum_limit=5.0,
                weekly_momentum_limit=5.0,
                cooldown_config=_MINIMAL_COOLDOWN_CONFIG,
            )
        assert req.cooldown_config is not None
        assert req.cooldown_bars == 48

    def test_bulk_old_and_new_no_error(self) -> None:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            req = BulkBacktestRequest(
                **_BASE_BULK,
                cooldown_bars=12,
                cooldown_config=_MINIMAL_COOLDOWN_CONFIG,
            )
        assert req.cooldown_config is not None
        assert req.cooldown_bars == 12


class TestJsonRoundTrip:
    """model_dump_json / model_validate_json preserves cooldown_config."""

    def test_backtest_request_round_trip(self) -> None:
        req = BacktestRequest(**_BASE_BACKTEST, cooldown_config=_MINIMAL_COOLDOWN_CONFIG)
        raw = req.model_dump_json()
        rehydrated = BacktestRequest.model_validate(json.loads(raw))
        assert rehydrated.cooldown_config == _MINIMAL_COOLDOWN_CONFIG

    def test_bulk_backtest_request_round_trip(self) -> None:
        req = BulkBacktestRequest(**_BASE_BULK, cooldown_config=_MINIMAL_COOLDOWN_CONFIG)
        raw = req.model_dump_json()
        rehydrated = BulkBacktestRequest.model_validate(json.loads(raw))
        assert rehydrated.cooldown_config == _MINIMAL_COOLDOWN_CONFIG

    def test_cooldown_config_absent_survives_round_trip(self) -> None:
        req = BacktestRequest(**_BASE_BACKTEST)
        raw = req.model_dump_json()
        rehydrated = BacktestRequest.model_validate(json.loads(raw))
        assert rehydrated.cooldown_config is None
