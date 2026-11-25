"""One-request transport contracts for bounded market microstructure reads."""

import json
from pathlib import Path

import httpx
import pytest

from mangrove_ai import MangroveAI, ServiceUnavailableError

SYMBOL = "COINBASE_SPOT_BTC_USD"
START = "2026-11-19T20:00:00-06:00"
END = "2026-11-20T02:01:00Z"
LEVELS_PAGE = json.loads((Path(__file__).parents[1] / "contracts/mangroveai/fixtures/liquidation-levels-page.json").read_text())


@pytest.mark.parametrize("method,path,args,params,payload", [
    (
        "get_orderbook", "/market-data/orderbook", (SYMBOL,),
        {"symbol_id": SYMBOL, "limit_levels": 20, "provider": "coinapi"},
        {"success": True, "symbol_id": SYMBOL, "provider": "coinapi",
         "bids": [[62000.25, 1.5]], "asks": [], "best_ask": None,
         "time_exchange": None, "time_coinapi": "2026-11-20T02:00:00.1234567Z"},
    ),
    (
        "get_orderbook_history", "/market-data/orderbook/history", (SYMBOL, START, END),
        {"symbol_id": SYMBOL, "time_start": START, "time_end": END,
         "limit": 100, "limit_levels": 20, "provider": "coinapi"},
        {"success": True, "symbol_id": SYMBOL, "provider": "coinapi", "data": [],
         "coverage": "bounded_provider_response", "limit_reached": False},
    ),
    (
        "get_order_flow", "/market-data/order-flow", (SYMBOL, START, END),
        {"symbol_id": SYMBOL, "time_start": START, "time_end": END,
         "limit": 100, "provider": "coinapi"},
        {"success": True, "symbol_id": SYMBOL, "provider": "coinapi",
         "data": [{"taker_side": "UNKNOWN", "size": 1, "price": 62000}],
         "summary": {"buy_quote_volume": 0, "sell_quote_volume": 0,
                     "unknown_quote_volume": 62000, "net_quote_volume": 0},
         "coverage": "bounded_provider_response", "limit_reached": True,
         "quality": {"skipped_records": 2, "duplicate_records": 1}},
    ),
    (
        "get_liquidation_levels", "/market-data/liquidation-levels", (),
        {"token_symbol": "BTC", "page": 1, "per_page": 100, "provider": "nansen"},
        LEVELS_PAGE,
    ),
])
def test_one_request_preserves_source_timestamps_nulls_and_coverage(client, method, path, args, params, payload):
    client._http.add_response("GET", path, json=payload)

    result = getattr(client.market_data, method)(*args)

    assert result == payload
    assert len(client._http.requests) == 1
    request = client._http.requests[0]
    assert request.method == "GET"
    assert request.params == params


def test_liquidation_page_is_explicit_and_not_automatically_followed(client):
    path = "/market-data/liquidation-levels"
    payload = {"data": [], "pagination": {"page": 7, "is_last_page": False}}
    client._http.add_response("GET", path, json=payload)

    assert client.market_data.get_liquidation_levels("ETH", page=7, per_page=25) == payload
    assert client._http.requests[0].params == {
        "token_symbol": "ETH", "page": 7, "per_page": 25, "provider": "nansen",
    }
    assert len(client._http.requests) == 1


def test_book_history_forwards_requested_bounds_without_normalizing_or_widening(client):
    path = "/market-data/orderbook/history"
    client._http.add_response("GET", path, json={"data": []})

    client.market_data.get_orderbook_history(SYMBOL, START, END, limit=17, limit_levels=50)

    assert client._http.requests[0].params == {
        "symbol_id": SYMBOL, "time_start": START, "time_end": END,
        "limit": 17, "limit_levels": 50, "provider": "coinapi",
    }


def test_provider_access_failure_is_preserved_without_fallback_or_retry():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(503, json={"error": "provider_unavailable"})

    with MangroveAI(
        api_key="prod_fixture_not_a_real_key", load_dotenv=False, auto_retry=False,
        httpx_client=httpx.Client(transport=httpx.MockTransport(handler)),
    ) as client, pytest.raises(ServiceUnavailableError) as error:
        client.market_data.get_liquidation_levels()
    assert error.value.status_code == 503
    assert len(seen) == 1
    assert seen[0].url.path == "/api/v1/market-data/liquidation-levels"
