from __future__ import annotations

from mangroveai import MangroveAI
from mangroveai._pagination import PaginatedResponse
from mangroveai._transport._mock import MockTransport
from mangroveai.models.shared import SuccessResponse
from mangroveai.models.strategies import (
    CreateStrategyRequest,
    StrategyDetail,
    StrategyListItem,
    UpdateStrategyRequest,
)

STRATEGY_DETAIL = {
    "id": "strat-uuid-1",
    "name": "BTC Momentum",
    "user_id": "user-uuid-1",
    "org_id": "org-uuid-1",
    "asset": "BTC",
    "rules": {
        "entry": [{"name": "rsi_oversold", "signal_type": "TRIGGER", "params": {"window": 14}}],
        "exit": [],
    },
    "status": "inactive",
    "created_at": "2026-04-11T00:00:00Z",
    "execution_config": {"max_risk_per_trade": 0.01},
    "execution_state": {"cash_balance": 10000},
    "content_hash": "abc123",
    "strategy_type": "momentum",
    "description": "RSI momentum strategy",
}


def _make_client(mock: MockTransport) -> MangroveAI:
    return MangroveAI(api_key="test_abc123", environment="local", httpx_client=mock)


class TestStrategiesList:
    def test_list_returns_paginated_response(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/strategies/", json={
            "success": True,
            "strategies": [
                {"id": "s1", "name": "Strat A", "asset": "BTC", "status": "inactive", "created_at": "2026-01-01T00:00:00Z"},
                {"id": "s2", "name": "Strat B", "asset": "ETH", "status": "paper", "created_at": "2026-01-02T00:00:00Z"},
            ],
            "total": 5,
            "skip": 0,
            "limit": 2,
        })
        client = _make_client(mock)

        result = client.strategies.list(skip=0, limit=2)

        assert isinstance(result, PaginatedResponse)
        assert len(result.items) == 2
        assert result.total == 5
        assert result.has_more is True
        assert isinstance(result.items[0], StrategyListItem)
        assert result.items[0].name == "Strat A"
        assert result.items[1].asset == "ETH"

    def test_list_iter_yields_items(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/strategies/", json={
            "success": True,
            "strategies": [
                {"id": "s1", "name": "Only One", "asset": "BTC", "status": "inactive", "created_at": "2026-01-01T00:00:00Z"},
            ],
            "total": 1,
            "skip": 0,
            "limit": 100,
        })
        client = _make_client(mock)

        items = list(client.strategies.list_iter())

        assert len(items) == 1
        assert items[0].name == "Only One"


class TestStrategiesCreate:
    def test_create_returns_detail(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/strategies/", json={
            "success": True,
            "strategy": STRATEGY_DETAIL,
        })
        client = _make_client(mock)

        request = CreateStrategyRequest(
            name="BTC Momentum",
            asset="BTC",
            entry=[{"name": "rsi_oversold", "signal_type": "TRIGGER", "params": {"window": 14}}],
        )
        result = client.strategies.create(request)

        assert isinstance(result, StrategyDetail)
        assert result.id == "strat-uuid-1"
        assert result.rules["entry"][0]["name"] == "rsi_oversold"
        assert mock.requests[0].json["name"] == "BTC Momentum"
        assert mock.requests[0].json["asset"] == "BTC"


class TestStrategiesGet:
    def test_get_returns_detail(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/strategies/strat-uuid-1", json={
            "success": True,
            "strategy": STRATEGY_DETAIL,
        })
        client = _make_client(mock)

        result = client.strategies.get("strat-uuid-1")

        assert isinstance(result, StrategyDetail)
        assert result.name == "BTC Momentum"
        assert result.execution_config == {"max_risk_per_trade": 0.01}


class TestStrategiesUpdate:
    def test_update_returns_detail(self) -> None:
        updated = {**STRATEGY_DETAIL, "name": "BTC Momentum v2"}
        mock = MockTransport()
        mock.add_response("PUT", "/strategies/strat-uuid-1", json={
            "success": True,
            "strategy": updated,
        })
        client = _make_client(mock)

        request = UpdateStrategyRequest(name="BTC Momentum v2")
        result = client.strategies.update("strat-uuid-1", request)

        assert result.name == "BTC Momentum v2"
        assert mock.requests[0].json == {"name": "BTC Momentum v2"}


class TestStrategiesDelete:
    def test_delete_returns_success(self) -> None:
        mock = MockTransport()
        mock.add_response("DELETE", "/strategies/strat-uuid-1", json={
            "success": True,
            "message": "Strategy deleted",
        })
        client = _make_client(mock)

        result = client.strategies.delete("strat-uuid-1")

        assert isinstance(result, SuccessResponse)
        assert result.success is True


class TestStrategiesStatus:
    def test_update_status(self) -> None:
        mock = MockTransport()
        mock.add_response("PATCH", "/strategies/strat-uuid-1/status", json={
            "success": True,
            "message": "Status updated to paper",
        })
        client = _make_client(mock)

        result = client.strategies.update_status("strat-uuid-1", "paper")

        assert result.success is True
        assert mock.requests[0].json == {"status": "paper"}


class TestStrategiesExecutionState:
    def test_update_execution_state(self) -> None:
        mock = MockTransport()
        mock.add_response("PATCH", "/strategies/strat-uuid-1/execution-state", json={
            "success": True,
            "message": "Execution state updated",
        })
        client = _make_client(mock)

        result = client.strategies.update_execution_state("strat-uuid-1", {"cash_balance": 5000})

        assert result.success is True
        assert mock.requests[0].json == {"cash_balance": 5000}
