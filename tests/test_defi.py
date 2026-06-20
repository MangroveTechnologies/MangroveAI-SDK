"""Tests for client.defi -- DeFiLlama analytics (free + Pro).

These verify each Pro method targets the right path and parses the
{success, count, data} envelope into its model. The tier-gate 403
(TIER_UPGRADE_REQUIRED -> AuthorizationError) is generic transport behavior the
mock harness does not exercise; it was verified live against the MangroveAI
endpoints in Phase 2 (pro -> 200, free -> 403 + upgrade message).
"""
from __future__ import annotations


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
