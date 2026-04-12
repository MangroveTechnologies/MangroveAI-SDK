from __future__ import annotations

import pytest

from mangroveai import MangroveAI
from mangroveai._transport._mock import MockTransport
from mangroveai.exceptions import TimeoutError
from mangroveai.models.backtesting import (
    AsyncBacktestStatus,
    AsyncBacktestSubmission,
    BacktestRequest,
    BacktestResult,
    BacktestTradesResponse,
    BulkBacktestRequest,
    BulkBacktestResult,
)


def _make_client(mock: MockTransport) -> MangroveAI:
    return MangroveAI(api_key="test_abc123", environment="local", httpx_client=mock)


BACKTEST_REQUEST = BacktestRequest(
    asset="BTC",
    interval="1d",
    strategy_json='{"name":"test","entry":[],"exit":[]}',
    initial_balance=10000,
    min_balance_threshold=0.1,
    min_trade_amount=25,
    max_open_positions=10,
    max_trades_per_day=50,
    max_risk_per_trade=0.01,
    max_units_per_trade=1000000,
    max_trade_amount=10000000,
    volatility_window=24,
    target_volatility=0.1,
    lookback_months=1,
)

BACKTEST_RESULT_JSON = {
    "success": True,
    "metrics": {"sharpe_ratio": 1.23, "win_rate": 0.55, "max_drawdown": 0.15},
    "trade_history": [
        {"entry_price": 95000, "exit_price": 97000, "profit_loss": 200, "exit_reason": "TP"}
    ],
    "execution_time_seconds": 3.21,
    "trade_count": 1,
    "strategy_names": ["test"],
}


class TestBacktestRun:
    def test_run_returns_result(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/backtesting/backtest", json=BACKTEST_RESULT_JSON)
        client = _make_client(mock)

        result = client.backtesting.run(BACKTEST_REQUEST)

        assert isinstance(result, BacktestResult)
        assert result.success is True
        assert result.metrics["sharpe_ratio"] == 1.23
        assert result.trade_count == 1
        assert len(result.trade_history) == 1


class TestBacktestRunBulk:
    def test_run_bulk_returns_results(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/backtesting/backtest/bulk", json={
            "success": True,
            "results": [
                {"success": True, "strategy_name": "Strat A", "metrics": {"sharpe_ratio": 1.4}, "trade_count": 38, "execution_time_seconds": 2.1},
                {"success": False, "strategy_name": "Strat B", "error": "Insufficient data", "trade_count": 0, "execution_time_seconds": 0.1},
            ],
            "data_fetches": 4,
            "total_execution_time_seconds": 8.7,
        })
        client = _make_client(mock)

        request = BulkBacktestRequest(
            start_date="2025-01-01",
            end_date="2025-06-01",
            initial_balance=10000,
            min_balance_threshold=0.1,
            min_trade_amount=25,
            max_open_positions=10,
            max_trades_per_day=50,
            max_risk_per_trade=0.01,
            max_units_per_trade=1000000,
            max_trade_amount=10000000,
            volatility_window=24,
            target_volatility=0.1,
            strategy_ids=["strat-1", "strat-2"],
        )
        result = client.backtesting.run_bulk(request)

        assert isinstance(result, BulkBacktestResult)
        assert len(result.results) == 2
        assert result.results[0].success is True
        assert result.results[1].success is False
        assert result.data_fetches == 4


class TestBacktestGet:
    def test_get_returns_result(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/backtesting/backtest/bt-uuid-1", json=BACKTEST_RESULT_JSON)
        client = _make_client(mock)

        result = client.backtesting.get("bt-uuid-1")

        assert isinstance(result, BacktestResult)
        assert result.success is True


class TestBacktestGetTrades:
    def test_get_trades_returns_response(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/backtesting/backtest/bt-uuid-1/trades", json={
            "success": True,
            "backtest_id": "bt-uuid-1",
            "trade_count": 2,
            "trades": [
                {"entry_price": 95000, "exit_price": 97000, "profit_loss": 200},
                {"entry_price": 96000, "exit_price": 94000, "profit_loss": -150},
            ],
        })
        client = _make_client(mock)

        result = client.backtesting.get_trades("bt-uuid-1")

        assert isinstance(result, BacktestTradesResponse)
        assert result.trade_count == 2
        assert len(result.trades) == 2


class TestBacktestAsync:
    def test_submit_async_returns_submission(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/backtests/", json={
            "backtest_id": "async-bt-1",
            "status": "running",
        })
        client = _make_client(mock)

        result = client.backtesting.submit_async(BACKTEST_REQUEST)

        assert isinstance(result, AsyncBacktestSubmission)
        assert result.backtest_id == "async-bt-1"
        assert result.status == "running"

    def test_poll_status_returns_status(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/backtests/async-bt-1/status", json={
            "backtest_id": "async-bt-1",
            "status": "completed",
            "metrics": {"sharpe_ratio": 1.5},
            "trade_history": [],
            "execution_time_seconds": 5.0,
        })
        client = _make_client(mock)

        result = client.backtesting.poll_status("async-bt-1")

        assert isinstance(result, AsyncBacktestStatus)
        assert result.status == "completed"

    def test_run_async_polls_until_complete(self) -> None:
        mock = MockTransport()
        # submit
        mock.add_response("POST", "/backtests/", json={
            "backtest_id": "async-bt-2",
            "status": "running",
        })
        # poll returns completed immediately
        mock.add_response("GET", "/backtests/async-bt-2/status", json={
            "backtest_id": "async-bt-2",
            "status": "completed",
            "metrics": {"sharpe_ratio": 2.0},
            "trade_history": [{"profit_loss": 100}],
            "execution_time_seconds": 4.0,
        })
        client = _make_client(mock)

        result = client.backtesting.run_async(BACKTEST_REQUEST, poll_interval=0.01)

        assert isinstance(result, BacktestResult)
        assert result.success is True
        assert result.metrics["sharpe_ratio"] == 2.0
        assert result.trade_count == 1

    def test_run_async_returns_failure(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/backtests/", json={
            "backtest_id": "async-bt-3",
            "status": "running",
        })
        mock.add_response("GET", "/backtests/async-bt-3/status", json={
            "backtest_id": "async-bt-3",
            "status": "failed",
            "error_message": "Insufficient data for BTC",
            "execution_time_seconds": 1.0,
        })
        client = _make_client(mock)

        result = client.backtesting.run_async(BACKTEST_REQUEST, poll_interval=0.01)

        assert result.success is False
        assert result.error == "Insufficient data for BTC"

    def test_run_async_timeout(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/backtests/", json={
            "backtest_id": "async-bt-4",
            "status": "running",
        })
        # Always returns running
        mock.add_response("GET", "/backtests/async-bt-4/status", json={
            "backtest_id": "async-bt-4",
            "status": "running",
        })
        client = _make_client(mock)

        with pytest.raises(TimeoutError, match="did not complete"):
            client.backtesting.run_async(BACKTEST_REQUEST, poll_interval=0.01, timeout=0.05)
