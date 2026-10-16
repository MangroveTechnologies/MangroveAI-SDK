"""Tests for on-chain series + token-flows label (mocked transport)."""
from __future__ import annotations

import pytest

from mangrove_ai import NotImplementedLayerError
from mangrove_ai.models.on_chain import OnChainSeriesResponse, TokenFlowsResponse


def test_get_onchain_series_parses_and_sends_body(client):
    client._http.add_response("POST", "/on-chain/series", json={
        "success": True,
        "symbol": "WETH",
        "chain": "ethereum",
        "interval": "1h",
        "metrics": ["SmartMoneyNetflow", "ExchangeNetflow"],
        "count": 2,
        "series": [
            {"timestamp": "2026-06-01T00:00:00", "SmartMoneyNetflow": 100.0, "ExchangeNetflow": -5.0},
            {"timestamp": "2026-06-01T01:00:00", "SmartMoneyNetflow": None, "ExchangeNetflow": 3.0},
        ],
    })
    resp = client.on_chain.get_onchain_series(
        "WETH", ["SmartMoneyNetflow", "ExchangeNetflow"],
        date_from="2026-06-01", date_to="2026-06-02", interval="1h", top_n=5,
    )
    assert isinstance(resp, OnChainSeriesResponse)
    assert resp.count == 2
    assert resp.metrics == ["SmartMoneyNetflow", "ExchangeNetflow"]
    assert resp.series[0]["SmartMoneyNetflow"] == 100.0
    assert resp.series[1]["SmartMoneyNetflow"] is None

    sent = client._http.requests[-1].json
    assert sent["symbol"] == "WETH"
    assert sent["metrics"] == ["SmartMoneyNetflow", "ExchangeNetflow"]
    assert sent["date_range"] == {"from": "2026-06-01", "to": "2026-06-02"}
    assert sent["interval"] == "1h" and sent["top_n"] == 5


@pytest.mark.parametrize("method,args", [
    ("get_whale_transactions", ()),
    ("get_exchange_flows", ()),
    ("get_whale_activity", ("BTC",)),
])
def test_retired_whalealert_methods_fail_before_network(client, method, args):
    with pytest.raises(NotImplementedLayerError, match="retired with the WhaleAlert provider"):
        getattr(client.on_chain, method)(*args)
    assert client._http.requests == []


def test_token_flows_label_in_body(client):
    client._http.add_response("POST", "/on-chain/token/WETH/flows", json={
        "success": True, "symbol": "WETH", "label": "whale", "count": 0, "flows": [],
    })
    resp = client.on_chain.get_token_flows("WETH", label="whale", date_from="2026-06-01", date_to="2026-06-02")
    assert isinstance(resp, TokenFlowsResponse)
    assert resp.label == "whale"
    assert client._http.requests[-1].json["label"] == "whale"
