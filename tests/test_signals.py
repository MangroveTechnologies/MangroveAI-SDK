from __future__ import annotations

from mangroveai import MangroveAI
from mangroveai._transport._mock import MockTransport
from mangroveai._pagination import PaginatedResponse
from mangroveai.models.signals import (
    Signal,
    SearchSignalsRequest,
    MatchResponse,
    EvaluateResponse,
    ValidationResponse,
)


def _make_client(mock: MockTransport) -> MangroveAI:
    return MangroveAI(api_key="test_abc123", environment="local", httpx_client=mock)


SIGNAL_JSON = {
    "name": "rsi_oversold",
    "category": "momentum",
    "signal_type": "TRIGGER",
    "metadata": {
        "rule_name": "rsi_oversold",
        "description": "RSI is below threshold",
        "requires": ["Close"],
        "params": {
            "window": {"type": "int", "min": 2, "max": 100, "default": 14},
            "threshold": {"type": "float", "min": 0.0, "max": 50.0, "default": 30.0},
        },
    },
    "code": "def rsi_oversold(df, window=14, threshold=30): ...",
    "usage_count": 42,
}


class TestSignalsList:
    def test_list_returns_paginated(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/signals/", json={
            "signals": [SIGNAL_JSON],
            "total": 96,
            "limit": 50,
            "offset": 0,
        })
        client = _make_client(mock)

        result = client.signals.list()

        assert isinstance(result, PaginatedResponse)
        assert len(result.items) == 1
        assert result.total == 96
        assert result.has_more is True
        assert isinstance(result.items[0], Signal)
        assert result.items[0].name == "rsi_oversold"
        assert result.items[0].metadata.params["window"]["default"] == 14

    def test_list_iter_yields_items(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/signals/", json={
            "signals": [SIGNAL_JSON],
            "total": 1,
            "limit": 50,
            "offset": 0,
        })
        client = _make_client(mock)

        items = list(client.signals.list_iter())

        assert len(items) == 1
        assert items[0].category == "momentum"


class TestSignalsGet:
    def test_get_returns_signal(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/signals/rsi_oversold", json=SIGNAL_JSON)
        client = _make_client(mock)

        result = client.signals.get("rsi_oversold")

        assert isinstance(result, Signal)
        assert result.name == "rsi_oversold"
        assert result.signal_type == "TRIGGER"
        assert result.usage_count == 42


class TestSignalsSearch:
    def test_search_returns_paginated(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/signals/search", json={
            "signals": [SIGNAL_JSON],
            "total": 1,
            "limit": 50,
            "offset": 0,
            "search_type": "name",
        })
        client = _make_client(mock)

        request = SearchSignalsRequest(query="rsi", search_type="name")
        result = client.signals.search(request)

        assert isinstance(result, PaginatedResponse)
        assert len(result.items) == 1
        assert mock.requests[0].json["query"] == "rsi"
        assert mock.requests[0].json["search_type"] == "name"


class TestSignalsMatch:
    def test_match_returns_results(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/signals/match", json={
            "query": "oversold momentum signal",
            "top_k": 5,
            "similarity_threshold": 0.5,
            "matches": [
                {
                    "signal_name": "rsi_oversold",
                    "description": "RSI below threshold",
                    "similarity_score": 0.92,
                    "semantic_score": 0.88,
                    "intent_score": 0.95,
                    "usecase_score": 0.90,
                    "params": {"window": 14, "threshold": 30},
                    "match_reasoning": "High relevance to oversold conditions",
                },
            ],
        })
        client = _make_client(mock)

        result = client.signals.match("oversold momentum signal", top_k=5)

        assert isinstance(result, MatchResponse)
        assert len(result.matches) == 1
        assert result.matches[0].signal_name == "rsi_oversold"
        assert result.matches[0].similarity_score == 0.92
        assert mock.requests[0].json["description"] == "oversold momentum signal"


class TestSignalsEvaluate:
    def test_evaluate_returns_result(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/signals/rsi_oversold/evaluate", json={
            "success": True,
            "result": True,
            "error": None,
        })
        client = _make_client(mock)

        result = client.signals.evaluate(
            "rsi_oversold",
            market_data=[{"Close": 100.0, "Open": 101.0, "High": 102.0, "Low": 99.0, "Volume": 1000}],
            parameters={"window": 14, "threshold": 30},
        )

        assert isinstance(result, EvaluateResponse)
        assert result.success is True
        assert result.result is True
        assert mock.requests[0].json["parameters"]["window"] == 14


class TestSignalsValidate:
    def test_validate_returns_response(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/signals/validate", json={
            "valid": True,
            "errors": [],
        })
        client = _make_client(mock)

        result = client.signals.validate(
            code="def my_signal(df, window=14): return df['Close'] > df['Close'].rolling(window).mean()",
            params={"window": {"type": "int", "min": 2, "max": 100, "default": 14}},
            description="Price above SMA",
        )

        assert isinstance(result, ValidationResponse)
        assert result.valid is True
        assert result.errors == []

    def test_validate_with_errors(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/signals/validate", json={
            "valid": False,
            "errors": ["Missing return statement", "Invalid parameter 'foo'"],
        })
        client = _make_client(mock)

        result = client.signals.validate(code="bad code", params={}, description="")

        assert result.valid is False
        assert len(result.errors) == 2
