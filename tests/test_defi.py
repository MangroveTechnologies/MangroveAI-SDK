"""Offline DeFi request and response contract tests."""
from __future__ import annotations

import pytest


class TestDefiProMethods:
    """The Pro methods map to the tier-gated MangroveAI /defi/* endpoints and
    return the {success, count, data} envelope."""

    def test_get_token_unlocks(self, client) -> None:
        client._http.add_response(
            "GET", "/defi/token-unlocks",
            json={"success": True, "count": 2, "data": [{"token": "ARB"}, {"token": "OP"}]},
        )
        r = client.defi.get_token_unlocks()
        assert r.success is True
        assert r.count == 2
        assert r.data[0]["token"] == "ARB"

    def test_get_perp_funding(self, client) -> None:
        client._http.add_response(
            "GET", "/defi/perp-funding",
            json={"success": True, "count": 1, "data": [{"pool": "GMX-ETH", "apy": 12.3}]},
        )
        r = client.defi.get_perp_funding()
        assert r.success is True and r.count == 1
        assert r.data[0]["pool"] == "GMX-ETH"

    def test_get_treasuries(self, client) -> None:
        client._http.add_response(
            "GET", "/defi/treasuries",
            json={"success": True, "count": 3, "data": [{"name": "Uniswap"}]},
        )
        assert client.defi.get_treasuries().count == 3

    def test_get_etf_flows(self, client) -> None:
        client._http.add_response(
            "GET", "/defi/etf-flows",
            json={"success": True, "count": 1, "data": [{"day": "2026-06-20", "total_flow_usd": 1.2e8}]},
        )
        r = client.defi.get_etf_flows()
        assert r.success is True
        assert r.data[0]["total_flow_usd"] == 1.2e8

    def test_get_lending_borrow_rates(self, client) -> None:
        client._http.add_response(
            "GET", "/defi/lending-rates",
            json={"success": True, "count": 1, "data": [{"pool": "aave-usdc", "borrow_apy": 5.1}]},
        )
        assert client.defi.get_lending_borrow_rates().data[0]["borrow_apy"] == 5.1


class TestDefiFreeMethods:
    """The free TVL methods are unchanged (regression guard)."""

    def test_get_protocol_tvl(self, client) -> None:
        client._http.add_response(
            "GET", "/defi/protocol/aave/tvl",
            json={"success": True, "protocol": "Aave V3", "tvl_usd": 1.24e10,
                  "chains": {"Ethereum": 1.0e10}, "data": {}},
        )
        r = client.defi.get_protocol_tvl("aave")
        assert r.success is True and r.tvl_usd == 1.24e10
        assert r.chains["Ethereum"] == 1.0e10


@pytest.mark.parametrize("method,path,filters", [
    ("get_token_unlocks", "token-unlocks", {"symbol": "ARB", "protocol": "arbitrum", "days_ahead": 60,
                                           "rank_by": "cliff_value_usd"}),
    ("get_perp_funding", "perp-funding", {"symbol": "BTC", "venue": "Binance"}),
    ("get_perp_funding_rates", "perp-funding", {"symbol": "ETH", "venue": "OKX"}),
    ("get_treasuries", "treasuries", {"symbol": "UNI", "protocol": "Uniswap"}),
    ("get_etf_flows", "etf-flows", {"symbol": "BTC", "lookback_days": 14}),
    ("get_lending_borrow_rates", "lending-rates", {"symbol": "USDC", "protocol": "aave-v3",
                                                 "chain": "Ethereum", "min_tvl_usd": 0}),
    ("get_lending_rates", "lending-rates", {"symbol": "USDT", "protocol": "aave-v3",
                                           "chain": "Arbitrum", "min_tvl_usd": 1_000_000}),
])
def test_pro_filters_and_paging_reach_transport(client, method, path, filters):
    client._http.add_response("GET", f"/defi/{path}", json={
        "success": True, "data": [{"symbol": "fixture"}], "count": 1,
        "total": 41, "limit": 1, "offset": 25, "has_more": True, "next_offset": 26, "skipped": 3,
    })
    result = getattr(client.defi, method)(**filters, limit=10, offset=25)
    assert client._http.requests[-1].params == {**filters, "limit": 10, "offset": 25}
    assert result.count == 1 and result.total == 41
    assert result.offset == 25 and result.limit == 1
    assert result.has_more is True and result.next_offset == 26 and result.skipped == 3
    # Continue with the server's offset even when it returned less than requested.
    getattr(client.defi, method)(**filters, limit=10, offset=result.next_offset)
    assert client._http.requests[-1].params["offset"] == 26


@pytest.mark.parametrize("method,path", [
    ("get_token_unlocks", "token-unlocks"), ("get_perp_funding", "perp-funding"),
    ("get_treasuries", "treasuries"), ("get_etf_flows", "etf-flows"),
    ("get_lending_borrow_rates", "lending-rates"),
])
def test_legacy_response_has_unknown_paging_not_false_completeness(client, method, path):
    client._http.add_response("GET", f"/defi/{path}", json={"success": True, "count": 1, "data": [{}]})
    result = getattr(client.defi, method)()
    assert result.total is None and result.has_more is None and result.next_offset is None
    assert all(value is not None for value in client._http.requests[-1].params.values())


def test_etf_window_totals_are_not_replaced_by_page_counts(client):
    client._http.add_response("GET", "/defi/etf-flows", json={
        "success": True, "count": 1, "data": [], "total": 30, "has_more": False, "next_offset": None,
        "window": {"lookback_days": 30}, "totals": [{"asset": "bitcoin", "net_flow_usd": 1000.0, "inflow_usd": 1500.0, "outflow_usd": -500.0, "days": 30}],
    })
    result = client.defi.get_etf_flows()
    assert result.totals == [{"asset": "bitcoin", "net_flow_usd": 1000.0, "inflow_usd": 1500.0, "outflow_usd": -500.0, "days": 30}]
    assert result.window == {"lookback_days": 30}
    assert result.has_more is False and result.next_offset is None
