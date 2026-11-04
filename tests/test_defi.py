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
        assert client._http.requests[-1].params == {"limit": 20, "offset": 0}
        assert r.has_more is None  # Legacy envelopes do not claim completeness.
        assert r.next_offset is None

    def test_token_unlock_pagination_preserves_server_cursor_and_complete_records(self) -> None:
        import httpx

        from mangrove_ai import MangroveAI

        first = {"token": "SYNTHETIC-A", "schedule": [{"timestamp": 123, "amount": "42.5"}]}
        second = {"token": "SYNTHETIC-B", "schedule": []}
        seen = []

        def respond(request):
            seen.append(dict(request.url.params))
            offset = int(request.url.params["offset"])
            page = [first] if offset == 0 else [second]
            return httpx.Response(200, json={
                "success": True, "provider": "defillama", "count": 1,
                "data": page, "records": page, "total_count": 2,
                "limit": 20, "offset": offset, "has_more": offset == 0,
                "next_offset": 1 if offset == 0 else None,
            })

        with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
            with MangroveAI(api_key="test_fixture", base_url="https://fixture.invalid/api/v1",
                            httpx_client=transport, load_dotenv=False, auto_retry=False) as sdk:
                page_one = sdk.defi.get_token_unlocks()
                assert len(seen) == 1  # Reading a page never automatically bills another call.
                assert page_one.records == page_one.data == [first]
                assert page_one.count == 1 and page_one.total_count == 2
                assert page_one.has_more is True and page_one.next_offset == 1
                page_two = sdk.defi.get_token_unlocks(limit=20, offset=page_one.next_offset)
                assert page_two.data == [second]
                assert page_two.offset == 1 and page_two.limit == 20
                assert page_two.has_more is False and page_two.next_offset is None
        assert seen == [{"limit": "20", "offset": "0"}, {"limit": "20", "offset": "1"}]

    def test_token_unlock_empty_page_remains_empty(self, client) -> None:
        client._http.add_response("GET", "/defi/token-unlocks", json={
            "success": True, "count": 0, "data": [], "records": [],
            "total_count": 2, "limit": 5, "offset": 7, "has_more": False, "next_offset": None,
        })
        page = client.defi.get_token_unlocks(limit=5, offset=7)
        assert page.data == page.records == []
        assert page.count == 0 and page.total_count == 2
        assert page.next_offset is None and page.has_more is False
        assert client._http.requests[-1].params == {"limit": 5, "offset": 7}

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
