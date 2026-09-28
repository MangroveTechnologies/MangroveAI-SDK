from __future__ import annotations

import traceback

import httpx
import pytest

from mangrove_ai import MangroveAI
from mangrove_ai._pagination import PaginatedResponse
from mangrove_ai._transport._mock import MockTransport
from mangrove_ai.exceptions import (
    MalformedResponseError,
    ServiceUnavailableError,
    ValidationError,
)
from mangrove_ai.models.signals import (
    EvaluateResponse,
    MatchResponse,
    SearchSignalsRequest,
    Signal,
    ValidationResponse,
)


def _make_client(mock: MockTransport) -> MangroveAI:
    return MangroveAI(api_key="test_abc123", environment="local", httpx_client=mock)


def _erroring_client(status: int, body: dict) -> MangroveAI:
    """A client on the real transport, so error responses go through its status mapping.

    (MockTransport returns canned responses without raising, so it cannot exercise
    that path.)
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)

    return MangroveAI(
        api_key="test_abc123",
        environment="local",
        auto_retry=False,
        httpx_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


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

    def test_list_forwards_category_filter(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/signals/", json={
            "signals": [SIGNAL_JSON],
            "total": 1,
            "limit": 10,
            "offset": 0,
        })
        client = _make_client(mock)

        result = client.signals.list(category="momentum", limit=10)

        assert len(result.items) == 1
        assert mock.requests[0].params["category"] == "momentum"
        assert mock.requests[0].params["limit"] == 10

    def test_list_omits_category_when_not_given(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/signals/", json={
            "signals": [SIGNAL_JSON],
            "total": 1,
            "limit": 50,
            "offset": 0,
        })
        client = _make_client(mock)

        client.signals.list()

        assert "category" not in mock.requests[0].params

    def test_list_iter_forwards_category_filter(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/signals/", json={
            "signals": [SIGNAL_JSON],
            "total": 1,
            "limit": 50,
            "offset": 0,
        })
        client = _make_client(mock)

        items = list(client.signals.list_iter(category="momentum"))

        assert len(items) == 1
        assert mock.requests[0].params["category"] == "momentum"


class TestSignalsListFilters:
    def _mock(self, **body: object) -> MockTransport:
        mock = MockTransport()
        mock.add_response("GET", "/signals/", json={
            "signals": [SIGNAL_JSON],
            "total": 1,
            "limit": 50,
            "offset": 0,
            **body,
        })
        return mock

    def test_forwards_regime_direction(self) -> None:
        mock = self._mock()
        _make_client(mock).signals.list(regime_direction="bear")

        assert mock.requests[0].params["regime_direction"] == "bear"

    def test_forwards_role(self) -> None:
        mock = self._mock()
        _make_client(mock).signals.list(role="TRIGGER")

        assert mock.requests[0].params["role"] == "TRIGGER"

    def test_forwards_every_filter_together(self) -> None:
        mock = self._mock()
        _make_client(mock).signals.list(
            category="momentum", regime_direction="bull", role="FILTER"
        )

        params = mock.requests[0].params
        assert params["category"] == "momentum"
        assert params["regime_direction"] == "bull"
        assert params["role"] == "FILTER"

    def test_omits_filters_that_were_not_supplied(self) -> None:
        mock = self._mock()
        _make_client(mock).signals.list()

        params = mock.requests[0].params
        assert "category" not in params
        assert "regime_direction" not in params
        assert "role" not in params

    def test_an_unrecognised_filter_value_is_sent_for_the_server_to_judge(self) -> None:
        # The accepted values live on the server. Enforcing a copy of them here would
        # reject a value the server has started accepting until the client is released.
        mock = self._mock()
        _make_client(mock).signals.list(role="not_a_role")

        assert mock.requests[0].params["role"] == "not_a_role"

    def test_list_iter_forwards_the_filters(self) -> None:
        mock = self._mock()
        list(_make_client(mock).signals.list_iter(regime_direction="bear", role="FILTER"))

        params = mock.requests[0].params
        assert params["regime_direction"] == "bear"
        assert params["role"] == "FILTER"


class TestSignalsListResponse:
    def test_reported_paging_is_exposed(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/signals/", json={
            "signals": [SIGNAL_JSON],
            "total": 96,
            "limit": 30,
            "offset": 0,
            "has_more": True,
            "next_offset": 30,
        })

        result = _make_client(mock).signals.list(limit=50)

        assert result.limit == 30
        assert result.has_more is True
        assert result.next_offset == 30

    def test_filter_metadata_is_exposed(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/signals/", json={
            "signals": [SIGNAL_JSON],
            "total": 1,
            "limit": 50,
            "offset": 0,
            "filter": {
                "regime_direction": "bear",
                "role": "TRIGGER",
                "before_filter": 96,
                "after_filter": 1,
            },
        })

        result = _make_client(mock).signals.list(regime_direction="bear", role="TRIGGER")

        assert result.filter is not None
        assert result.filter.regime_direction == "bear"
        assert result.filter.before_filter == 96
        assert result.filter.after_filter == 1

    def test_filter_metadata_is_absent_when_nothing_was_narrowed(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/signals/", json={
            "signals": [SIGNAL_JSON],
            "total": 1,
            "limit": 50,
            "offset": 0,
            "filter": None,
        })

        result = _make_client(mock).signals.list()

        assert result.filter is None

    def test_a_body_without_a_signal_list_is_an_error_not_an_empty_page(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/signals/", json={"total": 0, "limit": 50, "offset": 0})

        with pytest.raises(MalformedResponseError):
            _make_client(mock).signals.list()

    @pytest.mark.parametrize("signals", [None, {}, "", "invalid", 0, False])
    def test_a_signal_list_with_the_wrong_type_is_rejected(self, signals: object) -> None:
        client = _erroring_client(200, {"signals": signals, "total": 0})

        with pytest.raises(MalformedResponseError):
            client.signals.list()

    @pytest.mark.parametrize("record", [None, {}, "invalid", 7])
    def test_invalid_signal_records_raise_an_sdk_error(self, record: object) -> None:
        client = _erroring_client(200, {"signals": [record], "total": 1})

        with pytest.raises(MalformedResponseError):
            client.signals.list()

    def test_malformed_response_traceback_does_not_expose_input(self) -> None:
        client = _erroring_client(200, {
            "signals": [{"name": {"private": "PRIVATE_PAYLOAD_MARKER"}, "category": "trend"}],
        })

        with pytest.raises(MalformedResponseError) as error:
            client.signals.list()

        rendered = "".join(traceback.format_exception(error.type, error.value, error.tb))
        assert "PRIVATE_PAYLOAD_MARKER" not in rendered
        assert "input_value" not in rendered

    @pytest.mark.parametrize("field,value", [
        ("total", -1), ("offset", -1), ("limit", 0), ("limit", -1), ("next_offset", -1),
    ])
    def test_impossible_page_bounds_raise_an_sdk_error(self, field: str, value: int) -> None:
        client = _erroring_client(200, {
            "signals": [SIGNAL_JSON], "total": 2, "offset": 0, "limit": 1,
            "has_more": True, "next_offset": 1, field: value,
        })

        with pytest.raises(MalformedResponseError):
            client.signals.list()

    @pytest.mark.parametrize("field,value", [
        ("total", "invalid"), ("offset", "invalid"), ("limit", {}),
        ("has_more", "invalid"), ("next_offset", {}), ("filter", "invalid"),
    ])
    def test_invalid_page_metadata_raises_an_sdk_error(self, field: str, value: object) -> None:
        body = {"signals": [SIGNAL_JSON], "total": 2, "offset": 0, "limit": 1,
                "has_more": True, "next_offset": 1, field: value}
        client = _erroring_client(200, body)

        with pytest.raises(MalformedResponseError):
            client.signals.list()

    def test_a_valid_empty_list_is_still_successful(self) -> None:
        client = _erroring_client(200, {
            "signals": [], "total": 0, "offset": 0, "limit": 50,
            "has_more": False, "next_offset": None,
        })

        page = client.signals.list()

        assert page.items == []
        assert page.has_more is False
        assert page.next_offset is None

    def test_a_rejected_page_bound_raises(self) -> None:
        client = _erroring_client(400, {
            "error": "validation_error",
            "message": "limit must be at least 1",
            "code": "INVALID_REQUEST",
        })

        with pytest.raises(ValidationError):
            client.signals.list(limit=0)

    def test_a_rejected_filter_value_raises(self) -> None:
        client = _erroring_client(400, {
            "error": "validation_error",
            "message": "role must be one of TRIGGER, FILTER",
            "code": "INVALID_REQUEST",
        })

        with pytest.raises(ValidationError):
            client.signals.list(role="not_a_role")

    def test_an_unloaded_catalogue_is_distinct_from_an_empty_result(self) -> None:
        client = _erroring_client(503, {
            "error": "service_unavailable",
            "message": "signal catalogue is not loaded",
            "code": "CATALOGUE_UNAVAILABLE",
        })

        with pytest.raises(ServiceUnavailableError):
            client.signals.list()


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
