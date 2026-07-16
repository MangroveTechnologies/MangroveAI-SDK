"""Tests for the UsersService — authenticated-user metrics/strategies/backtests.

Closes the SDK coverage gap behind MangroveAI#863: the dev-portal quickstart
advertised client.users.me.metrics() but the SDK had no users resource at all.
"""
from __future__ import annotations

from mangrove_ai import MangroveAI
from mangrove_ai._transport._mock import MockTransport
from mangrove_ai.models.users import UserBacktest, UserMetrics, UserStrategy


def _client(mock: MockTransport) -> MangroveAI:
    return MangroveAI(api_key="test_abc123", environment="local", httpx_client=mock)


class TestUserMetrics:
    def test_get_my_metrics_unwraps_and_types(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/users/me/metrics", json={
            "success": True,
            "metrics": {
                "conversations_count": 3,
                "messages_count": 42,
                "estimated_tokens": 12345,
                "token_breakdown": {
                    "system_tokens": 100, "context_tokens": 200,
                    "user_tokens": 300, "assistant_tokens": 400, "total_tokens": 1000,
                },
                "strategies_count": 5,
                "backtests_count": 7,
                "tool_calls": {"list_signals": 2},
            },
        })
        m = _client(mock).users.get_my_metrics()
        assert isinstance(m, UserMetrics)
        assert m.conversations_count == 3
        assert m.token_breakdown is not None and m.token_breakdown.total_tokens == 1000
        assert m.tool_calls == {"list_signals": 2}


class TestUserStrategies:
    def test_get_my_strategies_returns_paginated(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/users/me/strategies", json={
            "success": True,
            "total": 1,
            "strategies": [{
                "id": "s1", "name": "ETH momentum", "asset": "ETH",
                "status": "active", "entry_signals": ["rsi_oversold"],
                "exit_signals": [], "archived": False,
            }],
        })
        page = _client(mock).users.get_my_strategies(status="active", limit=10)
        assert page.total == 1
        assert page.items[0].name == "ETH momentum"
        assert isinstance(page.items[0], UserStrategy)


class TestUserBacktests:
    def test_get_my_backtests_returns_paginated_with_verdict(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/users/me/backtests", json={
            "success": True,
            "total": 1,
            "backtests": [{
                "id": "b1", "asset": "BTC", "status": "completed",
                "total_trades": 30, "sharpe_ratio": 1.42, "result": "PASS",
            }],
        })
        page = _client(mock).users.get_my_backtests(asset="BTC")
        assert page.total == 1
        assert isinstance(page.items[0], UserBacktest)
        assert page.items[0].result == "PASS"
        assert page.items[0].sharpe_ratio == 1.42
