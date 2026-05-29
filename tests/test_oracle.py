"""Tests for the OracleService — SIEVE scoring, data query, backtest variants."""
from __future__ import annotations

import pytest

from mangrove_ai import MangroveAI
from mangrove_ai._transport._mock import MockTransport
from mangrove_ai.models.oracle import (
    DataQueryFilter,
    DataQueryRequest,
    DataQueryResponse,
    OracleAsyncBacktestStatus,
    OracleAsyncBacktestSubmission,
    OracleBacktestRequest,
    OracleBacktestResult,
    OracleBulkBacktestRequest,
    OracleBulkBacktestResult,
    RunInput,
    SieveScoreRequest,
    SieveScoreResponse,
    SignalSpec,
    StrategyInput,
)


def _make_client(mock: MockTransport) -> MangroveAI:
    return MangroveAI(api_key="test_abc123", environment="local", httpx_client=mock)


# Sample fixtures lifted from the real AVAX response in the corpus parity run
_SIEVE_RESPONSE = {
    "predictions": [
        {
            "binary": {"p_no_trades": 0.0000, "p_trades": 0.9999},
            "four_class": {
                "losing": 0.2426,
                "no_trades": 0.0000,
                "wash": 0.0596,
                "winning": 0.6977,
            },
        }
    ],
    "count": 1,
    "model_version": "mangrove-sieve:0b9a2da0d827",
    "code_version": "oracle:v0.14.1 ai:v3.10.1 kb:1.0.5 roots:v0.3.0",
}


def _strategy() -> StrategyInput:
    return StrategyInput(
        asset="AVAX",
        entry=[
            SignalSpec(
                name="bb_upper_breakout",
                signal_type="TRIGGER",
                params={"window": 95},
            )
        ],
        exit=[
            SignalSpec(
                name="macd_bearish_cross",
                signal_type="TRIGGER",
                params={"fast": 12, "slow": 26},
            )
        ],
    )


class TestSieveScore:
    def test_score_with_strategies_posts_correct_payload(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/oracle/sieve/score", json=_SIEVE_RESPONSE)
        client = _make_client(mock)

        result = client.oracle.sieve_score(
            SieveScoreRequest(strategies=[_strategy()])
        )

        assert isinstance(result, SieveScoreResponse)
        assert result.count == 1
        assert result.model_version == "mangrove-sieve:0b9a2da0d827"
        assert result.predictions[0].binary["p_trades"] == pytest.approx(0.9999)
        assert result.predictions[0].four_class["winning"] == pytest.approx(0.6977)

    def test_score_with_runs_posts_correct_payload(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/oracle/sieve/score", json=_SIEVE_RESPONSE)
        client = _make_client(mock)

        run = RunInput(
            entry_json='[{"name":"bb_upper_breakout","signal_type":"TRIGGER","params":{"window":95}}]',
            exit_json='[{"name":"macd_bearish_cross","signal_type":"TRIGGER","params":{"fast":12,"slow":26}}]',
            asset="AVAX",
            exec_config={"reward_factor": 2.0, "max_risk_per_trade": 0.01},
        )
        result = client.oracle.sieve_score(SieveScoreRequest(runs=[run]))
        assert result.count == 1

    def test_score_rejects_over_99_items_client_side(self) -> None:
        mock = MockTransport()
        client = _make_client(mock)
        request = SieveScoreRequest(strategies=[_strategy()] * 100)
        with pytest.raises(ValueError, match="Max 99"):
            client.oracle.sieve_score(request)

    def test_score_rejects_both_inputs(self) -> None:
        mock = MockTransport()
        client = _make_client(mock)
        run = RunInput(
            entry_json="[]", exit_json="[]", asset="AVAX", exec_config={}
        )
        request = SieveScoreRequest(strategies=[_strategy()], runs=[run])
        with pytest.raises(ValueError, match="exactly one"):
            client.oracle.sieve_score(request)

    def test_score_rejects_neither_input(self) -> None:
        mock = MockTransport()
        client = _make_client(mock)
        with pytest.raises(ValueError, match="exactly one"):
            client.oracle.sieve_score(SieveScoreRequest())


class TestDataQuery:
    def test_data_query_posts_correct_payload(self) -> None:
        mock = MockTransport()
        mock.add_response(
            "POST",
            "/oracle/data/query",
            json={
                "rows": [
                    {"experiment_id": "exp_X", "asset": "BTC", "irr_annualized": 52.3}
                ],
                "row_count": 1,
                "table": "results",
                "code_version": "oracle:v0.14.1 ai:v3.10.1 kb:1.0.5 roots:v0.3.0",
            },
        )
        client = _make_client(mock)

        request = DataQueryRequest(
            table="results",
            select=["experiment_id", "asset", "irr_annualized"],
            filters=[DataQueryFilter(col="irr_annualized", op=">=", value=50)],
            limit=5,
        )
        result = client.oracle.data_query(request)

        assert isinstance(result, DataQueryResponse)
        assert result.row_count == 1
        assert result.rows[0]["asset"] == "BTC"


class TestBacktest:
    def test_backtest_sync(self) -> None:
        mock = MockTransport()
        mock.add_response(
            "POST",
            "/oracle/backtest",
            json={
                "success": True,
                "metrics": {"sharpe_ratio": 1.5, "total_return": 22.3},
                "trade_count": 12,
                "strategy_names": ["AVAX bb breakout"],
            },
        )
        client = _make_client(mock)

        result = client.oracle.backtest(
            OracleBacktestRequest(asset="AVAX", interval="1h", strategy_json="{}")
        )

        assert isinstance(result, OracleBacktestResult)
        assert result.success is True
        assert result.metrics["sharpe_ratio"] == pytest.approx(1.5)

    def test_backtest_async_submission_and_poll(self) -> None:
        mock = MockTransport()
        mock.add_response(
            "POST",
            "/oracle/backtest/async",
            json={"backtest_id": "bt_123", "status": "running"},
        )
        mock.add_response(
            "GET",
            "/oracle/backtest/async/bt_123/status",
            json={
                "backtest_id": "bt_123",
                "status": "completed",
                "metrics": {"sharpe_ratio": 1.5},
                "trade_count": 12,
            },
        )
        client = _make_client(mock)

        submission = client.oracle.backtest_async(
            OracleBacktestRequest(asset="AVAX", interval="1h", strategy_json="{}")
        )
        assert isinstance(submission, OracleAsyncBacktestSubmission)
        assert submission.backtest_id == "bt_123"

        status = client.oracle.backtest_poll("bt_123")
        assert isinstance(status, OracleAsyncBacktestStatus)
        assert status.status == "completed"

    def test_backtest_bulk(self) -> None:
        mock = MockTransport()
        mock.add_response(
            "POST",
            "/oracle/backtest/bulk",
            json={
                "success": True,
                "results": [
                    {"strategy_name": "s1", "success": True, "metrics": {}, "trade_count": 10, "execution_time_seconds": 2.5}
                ],
                "data_fetches": 1,
                "total_execution_time_seconds": 2.5,
            },
        )
        client = _make_client(mock)

        result = client.oracle.backtest_bulk(
            OracleBulkBacktestRequest(
                start_date="2026-01-01",
                end_date="2026-04-01",
                initial_balance=10000,
                min_balance_threshold=0.1,
                min_trade_amount=25,
                max_open_positions=5,
                max_trades_per_day=50,
                max_risk_per_trade=0.01,
                max_units_per_trade=100,
                max_trade_amount=10000,
                volatility_window=24,
                target_volatility=0.02,
                volatility_mode="stddev",
                enable_volatility_adjustment=False,
                cooldown_bars=24,
                daily_momentum_limit=3.0,
                weekly_momentum_limit=3.0,
                strategy_configs=[{"name": "s1"}],
            )
        )

        assert isinstance(result, OracleBulkBacktestResult)
        assert result.success is True
        assert result.data_fetches == 1


# =============================================================================
# Experiments lifecycle
# =============================================================================


_EXPERIMENT_ID = "exp_20260529T120000000000Z"


class TestExperiments:
    def test_create_experiment_posts_config(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/oracle/experiments", json={
            "experiment_id": _EXPERIMENT_ID,
            "status": "draft",
            "created_at": "2026-05-29T12:00:00Z",
            "org_id": "org-abc",
        })
        client = _make_client(mock)

        from mangrove_ai.models.oracle import ExperimentCreated
        result = client.oracle.create_experiment({"name": "BTC momentum sweep"})

        assert isinstance(result, ExperimentCreated)
        assert result.experiment_id == _EXPERIMENT_ID
        assert result.status == "draft"
        assert mock.requests[-1].json == {"name": "BTC momentum sweep"}

    def test_list_experiments_parses_each_entry(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/oracle/experiments", json=[
            {
                "experiment_id": _EXPERIMENT_ID,
                "name": "BTC sweep",
                "status": "launched",
                "total_runs": 99,
                "completed": 42,
                "search_mode": "grid",
                "created_at": "2026-05-29T12:00:00Z",
            },
            {
                "experiment_id": "exp_other",
                "name": "ETH sweep",
                "status": "draft",
            },
        ])
        client = _make_client(mock)

        from mangrove_ai.models.oracle import ExperimentSummary
        summaries = client.oracle.list_experiments()

        assert len(summaries) == 2
        assert all(isinstance(s, ExperimentSummary) for s in summaries)
        assert summaries[0].completed == 42
        assert summaries[0].search_mode == "grid"

    def test_get_experiment_returns_full_dict(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", f"/oracle/experiments/{_EXPERIMENT_ID}", json={
            "experiment_id": _EXPERIMENT_ID,
            "name": "BTC sweep",
            "status": "draft",
            "datasets": ["btc_2024_1h"],
            "completed_runs": 0,
        })
        client = _make_client(mock)

        result = client.oracle.get_experiment(_EXPERIMENT_ID)

        assert result["experiment_id"] == _EXPERIMENT_ID
        assert result["datasets"] == ["btc_2024_1h"]
        assert result["completed_runs"] == 0

    def test_update_experiment(self) -> None:
        mock = MockTransport()
        mock.add_response("PUT", f"/oracle/experiments/{_EXPERIMENT_ID}", json={
            "experiment_id": _EXPERIMENT_ID,
            "status": "draft",
        })
        client = _make_client(mock)

        from mangrove_ai.models.oracle import ExperimentStatus
        result = client.oracle.update_experiment(
            _EXPERIMENT_ID,
            {"name": "BTC sweep v2", "datasets": ["btc_2024_1h"]},
        )

        assert isinstance(result, ExperimentStatus)
        assert mock.requests[-1].json == {"name": "BTC sweep v2", "datasets": ["btc_2024_1h"]}

    def test_delete_experiment(self) -> None:
        mock = MockTransport()
        mock.add_response("DELETE", f"/oracle/experiments/{_EXPERIMENT_ID}", json={
            "status": "deleted",
        })
        client = _make_client(mock)

        from mangrove_ai.models.oracle import ExperimentDeleted
        result = client.oracle.delete_experiment(_EXPERIMENT_ID)

        assert isinstance(result, ExperimentDeleted)
        assert result.status == "deleted"

    def test_validate_launch_pause_each_return_status(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", f"/oracle/experiments/{_EXPERIMENT_ID}/validate", json={
            "experiment_id": _EXPERIMENT_ID, "status": "validated",
        })
        mock.add_response("POST", f"/oracle/experiments/{_EXPERIMENT_ID}/launch", json={
            "experiment_id": _EXPERIMENT_ID, "status": "launched",
        })
        mock.add_response("POST", f"/oracle/experiments/{_EXPERIMENT_ID}/pause", json={
            "experiment_id": _EXPERIMENT_ID, "status": "paused",
        })
        client = _make_client(mock)

        assert client.oracle.validate_experiment(_EXPERIMENT_ID).status == "validated"
        assert client.oracle.launch_experiment(_EXPERIMENT_ID).status == "launched"
        assert client.oracle.pause_experiment(_EXPERIMENT_ID).status == "paused"


# =============================================================================
# Results
# =============================================================================


class TestResults:
    def test_list_results_paginated(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/oracle/results", json={
            "total": 99,
            "offset": 0,
            "limit": 10,
            "results": [
                {"experiment_id": _EXPERIMENT_ID, "asset": "BTC", "irr_annualized": 0.42},
                {"experiment_id": _EXPERIMENT_ID, "asset": "BTC", "irr_annualized": 0.31},
            ],
        })
        client = _make_client(mock)

        from mangrove_ai.models.oracle import OracleResultsPage
        page = client.oracle.list_results(experiment_id=_EXPERIMENT_ID, limit=10)

        assert isinstance(page, OracleResultsPage)
        assert page.total == 99
        assert len(page.results) == 2
        assert page.results[0]["irr_annualized"] == 0.42
        params = mock.requests[-1].params
        assert params == {"experiment_id": _EXPERIMENT_ID, "limit": 10, "offset": 0}


# =============================================================================
# Metadata catalogs
# =============================================================================


class TestOracleMetadata:
    def test_list_datasets(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/oracle/datasets", json=[
            {"asset": "BTC", "timeframe": "1h", "file": "btc_2024_1h.csv", "rows": 8760,
             "start_date": "2024-01-01", "end_date": "2024-12-31"},
        ])
        client = _make_client(mock)

        result = client.oracle.list_datasets()

        assert isinstance(result, list)
        assert result[0]["asset"] == "BTC"

    def test_list_signals(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/oracle/signals", json=[
            {"name": "macd_bullish_cross", "type": "TRIGGER", "category": "momentum",
             "params": {"window_fast": {"type": "int", "default": 12}},
             "requires": ["Close"]},
        ])
        client = _make_client(mock)

        result = client.oracle.list_signals()

        assert result[0]["name"] == "macd_bullish_cross"
        assert result[0]["type"] == "TRIGGER"

    def test_list_templates(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/oracle/templates", json=[])
        client = _make_client(mock)

        assert client.oracle.list_templates() == []
