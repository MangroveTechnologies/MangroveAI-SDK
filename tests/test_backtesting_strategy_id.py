"""Tests for backtesting a saved strategy by strategy_id (MangroveAI #629).

BacktestRequest now accepts exactly one of strategy_json or strategy_id, mirroring
run_bulk's strategy_ids and execution.evaluate(strategy_id).
"""
import pytest

from mangrove_ai.models.backtesting import BacktestRequest


def test_strategy_id_only_is_valid_and_omits_strategy_json():
    req = BacktestRequest(interval="1h", strategy_id="11111111-1111-1111-1111-111111111111")
    body = req.model_dump(exclude_none=True)
    assert body["strategy_id"] == "11111111-1111-1111-1111-111111111111"
    assert "strategy_json" not in body  # omitted so the server expands the id
    assert "asset" not in body          # server defaults asset from the saved strategy


def test_strategy_json_with_asset_still_valid():
    req = BacktestRequest(asset="BTC", interval="1h", strategy_json='{"entry":[],"exit":[]}')
    body = req.model_dump(exclude_none=True)
    assert body["strategy_json"] == '{"entry":[],"exit":[]}'
    assert body["asset"] == "BTC"
    assert "strategy_id" not in body


def test_both_sources_rejected():
    with pytest.raises(ValueError, match="exactly one"):
        BacktestRequest(asset="BTC", interval="1h", strategy_json="{}", strategy_id="abc")


def test_neither_source_rejected():
    with pytest.raises(ValueError, match="exactly one"):
        BacktestRequest(asset="BTC", interval="1h")


def test_strategy_json_requires_asset():
    with pytest.raises(ValueError, match="asset is required"):
        BacktestRequest(interval="1h", strategy_json="{}")
