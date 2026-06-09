"""Live round-trip tests for the Oracle surface — the contract-drift catcher.

The Oracle response models are hand-maintained mirrors of MangroveOracle's
shapes. They have repeatedly drifted from the server (validate/pause/data_query/
simulate/order_by) and shipped because nothing exercised them against a real
200. These tests call each Oracle method against the live API and assert the
typed model parses — so drift fails CI instead of crashing a customer.

Read-only / non-launching by design (no sweep launches → no quota burn): the
point is to validate response *shapes*, not to run experiments.

Requires MANGROVE_API_KEY. Run:
    MANGROVE_API_KEY=... pytest tests/integration/test_oracle_live.py -v -m integration
"""
from __future__ import annotations

import os

import pytest

from mangrove_ai import MangroveAI
from mangrove_ai.models.oracle import (
    DataQueryFilter,
    DataQueryRequest,
    DataQueryResponse,
    OrderBy,
    SieveScoreRequest,
    SieveScoreResponse,
    SimulateRunResponse,
)

API_KEY = os.environ.get("MANGROVE_API_KEY")
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client() -> MangroveAI:
    if not API_KEY:
        pytest.skip("MANGROVE_API_KEY not set")
    return MangroveAI(api_key=API_KEY)


# --- metadata catalogs (free) -------------------------------------------------

def test_list_datasets_parses(client: MangroveAI) -> None:
    ds = client.oracle.list_datasets()
    assert isinstance(ds, list)


def test_list_signals_parses(client: MangroveAI) -> None:
    sigs = client.oracle.list_signals()
    assert isinstance(sigs, list) and sigs


# --- data_query: the table-field + order_by drift (results AND ohlcv) ---------

def test_data_query_results_parses(client: MangroveAI) -> None:
    """Catches the `DataQueryResponse.table` required-field crash."""
    r = client.oracle.data_query(DataQueryRequest(
        table="results",
        select=["experiment_id", "asset", "sharpe_ratio"],
        filters=[DataQueryFilter(col="asset", op="=", value="BTC")],
        limit=3,
    ))
    assert isinstance(r, DataQueryResponse)


def test_data_query_ohlcv_not_org_scoped(client: MangroveAI) -> None:
    """Catches the unconditional-org_id 400 on the non-tenant ohlcv table."""
    r = client.oracle.data_query(DataQueryRequest(
        table="ohlcv", select=["asset", "close"],
        filters=[DataQueryFilter(col="asset", op="=", value="BTC")], limit=3,
    ))
    assert isinstance(r, DataQueryResponse)


def test_data_query_order_by_dict_shape(client: MangroveAI) -> None:
    """Catches the order_by string-vs-dict mismatch (server wants {col,dir})."""
    r = client.oracle.data_query(DataQueryRequest(
        table="results", select=["asset", "sharpe_ratio"],
        order_by=[OrderBy(col="sharpe_ratio", dir="desc")], limit=3,
    ))
    assert isinstance(r, DataQueryResponse)


# --- sieve + simulate ---------------------------------------------------------

def test_sieve_score_parses(client: MangroveAI) -> None:
    strat = {
        "asset": "BTC",
        "entry": [{"name": "macd_bullish_cross", "signal_type": "TRIGGER",
                   "timeframe": "1h", "params": {"window_fast": 12, "window_slow": 26}}],
        "exit": [{"name": "macd_bearish_cross", "signal_type": "TRIGGER",
                  "timeframe": "1h", "params": {"window_fast": 12, "window_slow": 26}}],
        "execution_config": {"reward_factor": 2.0, "max_risk_per_trade": 0.01},
    }
    r = client.oracle.sieve_score(SieveScoreRequest(strategies=[strat]))
    assert isinstance(r, SieveScoreResponse) and r.predictions


def test_simulate_run_parses(client: MangroveAI) -> None:
    """Catches the simulate_run silent-wrong drift (real fields, not simulation_id)."""
    presets = client.oracle.simulate_presets()
    if not presets:
        pytest.skip("no simulate presets available")
    r = client.oracle.simulate_run(presets[0])
    assert isinstance(r, SimulateRunResponse)
    # the real shape exposes metrics/trades, not a `result` blob
    assert hasattr(r, "metrics") and hasattr(r, "trades")
