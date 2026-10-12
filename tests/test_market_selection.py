import pytest

from mangrove_ai import MangroveAI
from mangrove_ai._transport._mock import MockTransport


@pytest.mark.parametrize("service,method,args,path,http_method", [
    ("crypto_assets", "get_market_data", {"symbol": "BTC"}, "/crypto-assets/market-data/BTC", "GET"),
    ("crypto_assets", "get_ohlcv", {"symbol": "BTC"}, "/crypto-assets/ohlcv/BTC", "GET"),
    ("market_data", "get_market_regime", {"asset": "BTC"}, "/market-data/regime/BTC", "GET"),
    ("market_data", "classify_market_segment", {"asset": "BTC", "start_date": "2026-10-01", "end_date": "2026-10-08"}, "/market-data/segment", "GET"),
    ("signals", "evaluate_multiple_series", {"symbol": "BTC", "signals": []}, "/signals/evaluate-multiple-series", "POST"),
])
def test_market_selection_reaches_server_once(service, method, args, path, http_method):
    market = {"provider": "mangrove", "quote_token": "USD", "market_data_venue": "KRAKEN"}
    mock = MockTransport()
    mock.add_response(http_method, path, json={
        "success": True, "symbol": "BTC", "asset": "BTC", "base_token": "BTC",
        "data": {}, "bars": 7, "regime": {}, **market})
    with MangroveAI(api_key="test_abc123", environment="local", httpx_client=mock) as client:
        result = getattr(getattr(client, service), method)(**args, **market)
    assert len(mock.requests) == 1
    request = mock.requests[0]
    fields = request.json if http_method == "POST" else request.params
    assert {key: fields[key] for key in market} == market
    if hasattr(result, "model_dump"):
        assert result.quote_token == "USD"
        assert result.market_data_venue == "KRAKEN"
    else:
        assert result["market_data_venue"] == "KRAKEN"
