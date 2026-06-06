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

    def test_validate_returns_validation_result(self) -> None:
        # Validate returns {valid, total_runs, errors, warnings} — NOT a
        # {experiment_id, status} transition. (Regression: the SDK used to
        # type this as ExperimentStatus and crashed on the real 200 body.)
        mock = MockTransport()
        mock.add_response("POST", f"/oracle/experiments/{_EXPERIMENT_ID}/validate", json={
            "valid": True, "total_runs": 12, "errors": [], "warnings": [],
        })
        client = _make_client(mock)

        from mangrove_ai.models.oracle import ExperimentValidation
        result = client.oracle.validate_experiment(_EXPERIMENT_ID)

        assert isinstance(result, ExperimentValidation)
        assert result.valid is True
        assert result.total_runs == 12

    def test_validate_surfaces_invalid_config(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", f"/oracle/experiments/{_EXPERIMENT_ID}/validate", json={
            "valid": False, "total_runs": 0,
            "errors": ["No entry filter signals selected"], "warnings": [],
        })
        client = _make_client(mock)

        result = client.oracle.validate_experiment(_EXPERIMENT_ID)
        assert result.valid is False
        assert "No entry filter signals selected" in result.errors

    def test_launch_returns_status(self) -> None:
        mock = MockTransport()
        # Real launch body carries status + experiment_id (+ total_runs).
        mock.add_response("POST", f"/oracle/experiments/{_EXPERIMENT_ID}/launch", json={
            "status": "preparing", "experiment_id": _EXPERIMENT_ID, "total_runs": 12,
        })
        client = _make_client(mock)
        assert client.oracle.launch_experiment(_EXPERIMENT_ID).status == "preparing"

    def test_pause_returns_status_without_experiment_id(self) -> None:
        # Pause returns {status: "paused"} alone — no experiment_id.
        # (Regression: experiment_id was required and crashed parsing this.)
        mock = MockTransport()
        mock.add_response("POST", f"/oracle/experiments/{_EXPERIMENT_ID}/pause", json={
            "status": "paused",
        })
        client = _make_client(mock)

        result = client.oracle.pause_experiment(_EXPERIMENT_ID)
        assert result.status == "paused"
        assert result.experiment_id is None


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


# ─── gh issue #576 fixes: exec_config / simulate / leaderboard / deployed ───


class TestExecConfigDefaults:
    """gh #576 issue #1: GET /oracle/exec-config used to return SPA HTML."""

    def test_exec_config_defaults_returns_dict(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/oracle/exec-config/defaults", json={
            "risk_management": {"position_size_calc": "v2", "max_risk_per_trade": 0.01},
            "position_limits": {"initial_balance": 10000.0, "max_open_positions": 1},
        })
        client = _make_client(mock)

        defaults = client.oracle.exec_config_defaults()

        assert defaults["risk_management"]["position_size_calc"] == "v2"
        assert defaults["position_limits"]["initial_balance"] == 10000.0


class TestSimulate:
    """gh #576 issue #2: GET /oracle/simulate bare path used to return SPA HTML.
    Real verbs live under /simulate/{run,generate,presets,history}."""

    def test_simulate_run_posts_body(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/oracle/simulate/run", json={
            "simulation_id": "sim-abc-123",
            "status": "complete",
            "result": {"irr_annualized": 0.42, "sharpe_ratio": 2.1},
        })
        client = _make_client(mock)

        resp = client.oracle.simulate_run({"strategy": {"asset": "BTC"}, "dataset_id": "ds-1"})

        assert resp.simulation_id == "sim-abc-123"
        assert resp.status == "complete"
        assert resp.result["irr_annualized"] == 0.42

    def test_simulate_presets_lists(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/oracle/simulate/presets", json=[
            {"id": "rsi_oversold_btc", "name": "RSI oversold BTC", "strategy": {}},
        ])
        client = _make_client(mock)

        presets = client.oracle.simulate_presets()

        assert len(presets) == 1
        assert presets[0]["id"] == "rsi_oversold_btc"

    def test_simulate_history_passes_pagination(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/oracle/simulate/history",
                          json={"total": 0, "results": []})
        client = _make_client(mock)

        hist = client.oracle.simulate_history(limit=10, offset=20)

        assert hist["total"] == 0


class TestLeaderboard:
    """gh #576 issue #4: /oracle/leaderboard returns curated personas, not
    strategy rankings (server is canonical post-restructure)."""

    def test_leaderboard_returns_personas(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/oracle/leaderboard", json={
            "personas": [
                {
                    "id": "marcus",
                    "name": "Marcus",
                    "avatar": "stethoscope",
                    "deployed_strategy_ids": ["dep-001", "dep-002"],
                    "rank": 1,
                },
                {
                    "id": "lina",
                    "name": "Lina",
                    "avatar": "violin",
                    "deployed_strategy_ids": ["dep-003"],
                    "rank": 2,
                },
            ]
        })
        client = _make_client(mock)

        lb = client.oracle.leaderboard()

        assert len(lb.personas) == 2
        assert lb.personas[0].name == "Marcus"
        assert lb.personas[0].rank == 1
        assert lb.personas[0].deployed_strategy_ids == ["dep-001", "dep-002"]


class TestDeployed:
    """gh #576 issue #4 (sibling): /oracle/deployed/* is the new home for
    live strategy state. Wrapped here so customers don't have to drop to
    raw httpx."""

    def test_list_deployed_strategies_dict_shape(self) -> None:
        """Server may return {"strategies": [...]} wrapper."""
        mock = MockTransport()
        mock.add_response("GET", "/oracle/deployed/strategies", json={
            "strategies": [
                {"strategy_id": "dep-001", "name": "BTC RSI Mean Reversion",
                 "asset": "BTC", "total_trades": 8, "health": "ok"},
            ]
        })
        client = _make_client(mock)

        strategies = client.oracle.list_deployed_strategies()

        assert len(strategies) == 1
        assert strategies[0].strategy_id == "dep-001"
        assert strategies[0].total_trades == 8
        assert strategies[0].health == "ok"

    def test_list_deployed_strategies_bare_list_shape(self) -> None:
        """Server may also return a bare list. Accept both."""
        mock = MockTransport()
        mock.add_response("GET", "/oracle/deployed/strategies", json=[
            {"strategy_id": "dep-002", "name": "ETH Momentum", "asset": "ETH"},
        ])
        client = _make_client(mock)

        strategies = client.oracle.list_deployed_strategies()

        assert len(strategies) == 1
        assert strategies[0].asset == "ETH"

    def test_get_deployed_strategy_state(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/oracle/deployed/dep-001/state", json={
            "cash_balance": 1234.56, "account_value": 10456.23,
            "num_open_positions": 1, "total_trades": 8,
        })
        client = _make_client(mock)

        state = client.oracle.get_deployed_strategy_state("dep-001")

        assert state["account_value"] == 10456.23
        assert state["num_open_positions"] == 1

    def test_get_deployed_strategy_events_passes_limit(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/oracle/deployed/dep-001/events",
                          json={"events": [{"type": "fill", "side": "buy"}]})
        client = _make_client(mock)

        events = client.oracle.get_deployed_strategy_events("dep-001", limit=10)

        assert len(events["events"]) == 1
        assert events["events"][0]["type"] == "fill"


class TestListResultsUnfiltered:
    """gh #576 issue #3 (SDK side): list_results(experiment_id=None) used to
    500 because of the Oracle BQ ORDER BY bug. Now that Oracle PR #237 is in,
    the SDK should accept None and omit the filter."""

    def test_list_results_with_none_experiment_id_omits_param(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/oracle/results",
                          json={"total": 5, "offset": 0, "limit": 100, "results": []})
        client = _make_client(mock)

        page = client.oracle.list_results(experiment_id=None, limit=100)

        assert page.total == 5
        # The recorded request should not include an empty experiment_id —
        # the SDK omits the param entirely when None so the server uses
        # the cross-experiment scan path.
        recorded = [r for r in mock.requests if r.method == "GET" and "/oracle/results" in r.url]
        assert len(recorded) == 1
        if recorded[0].params:
            assert "experiment_id" not in recorded[0].params
