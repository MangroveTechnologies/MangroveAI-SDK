from __future__ import annotations

from mangroveai import MangroveAI
from mangroveai._transport._mock import MockTransport
from mangroveai.models.execution import (
    Account,
    CreateAccountRequest,
    EvaluateResult,
    Position,
    Trade,
)


def _make_client(mock: MockTransport) -> MangroveAI:
    return MangroveAI(api_key="test_abc123", environment="local", httpx_client=mock)


ACCOUNT_JSON = {
    "id": "acct-uuid-1",
    "org_id": "org-uuid-1",
    "user_id": "user-uuid-1",
    "account_type": "paper",
    "name": "Paper Trading",
    "cash_balance": 10000.0,
    "account_value": 10000.0,
    "max_open_positions": 3,
    "max_trades_per_day": 10,
    "max_risk_per_trade": 0.02,
    "active": True,
    "created_at": "2026-04-01T00:00:00Z",
}

POSITION_JSON = {
    "id": "pos-uuid-1",
    "account_id": "acct-uuid-1",
    "strategy_id": "strat-uuid-1",
    "asset": "BTC-USD",
    "entry_price": 95000.0,
    "position_size": 0.1,
    "open": True,
    "stop_loss_price": 93000.0,
    "take_profit_price": 99000.0,
    "entry_timestamp": "2026-04-10T08:00:00Z",
}

TRADE_JSON = {
    "id": "trade-uuid-1",
    "account_id": "acct-uuid-1",
    "position_id": "pos-uuid-1",
    "outcome": "win",
    "profit_loss": 350.0,
    "profit_loss_pct": 3.68,
    "asset": "BTC-USD",
    "strategy_name": "BTC Momentum",
    "entry_price": 95000.0,
    "exit_price": 98500.0,
    "position_size": 0.1,
    "beginning_balance": 10000.0,
    "ending_balance": 10350.0,
    "closed_at": "2026-04-11T14:00:00Z",
}


class TestExecutionAccounts:
    def test_list_accounts(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/execution/accounts", json={
            "accounts": [ACCOUNT_JSON],
        })
        client = _make_client(mock)

        result = client.execution.list_accounts()

        assert len(result) == 1
        assert isinstance(result[0], Account)
        assert result[0].account_type == "paper"
        assert result[0].cash_balance == 10000.0

    def test_list_accounts_with_filter(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/execution/accounts", json={"accounts": []})
        client = _make_client(mock)

        client.execution.list_accounts(account_type="live")

        assert mock.requests[0].params["account_type"] == "live"

    def test_create_account(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/execution/accounts", json=ACCOUNT_JSON)
        client = _make_client(mock)

        request = CreateAccountRequest(account_type="paper", name="Paper Trading", initial_balance=10000)
        result = client.execution.create_account(request)

        assert isinstance(result, Account)
        assert result.id == "acct-uuid-1"
        assert mock.requests[0].json["account_type"] == "paper"

    def test_get_account(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/execution/accounts/acct-uuid-1", json=ACCOUNT_JSON)
        client = _make_client(mock)

        result = client.execution.get_account("acct-uuid-1")

        assert result.name == "Paper Trading"

    def test_update_account(self) -> None:
        updated = {**ACCOUNT_JSON, "name": "Renamed Account"}
        mock = MockTransport()
        mock.add_response("PUT", "/execution/accounts/acct-uuid-1", json=updated)
        client = _make_client(mock)

        result = client.execution.update_account("acct-uuid-1", name="Renamed Account")

        assert result.name == "Renamed Account"
        assert mock.requests[0].json == {"name": "Renamed Account"}


class TestExecutionPositions:
    def test_list_positions_array_response(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/execution/positions", json=[POSITION_JSON])
        client = _make_client(mock)

        result = client.execution.list_positions()

        assert len(result) == 1
        assert isinstance(result[0], Position)
        assert result[0].asset == "BTC-USD"
        assert result[0].open is True

    def test_list_positions_with_filters(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/execution/positions", json=[])
        client = _make_client(mock)

        client.execution.list_positions(account_id="acct-uuid-1", status="open")

        params = mock.requests[0].params
        assert params["account_id"] == "acct-uuid-1"
        assert params["status"] == "open"

    def test_get_position(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/execution/positions/pos-uuid-1", json=POSITION_JSON)
        client = _make_client(mock)

        result = client.execution.get_position("pos-uuid-1")

        assert isinstance(result, Position)
        assert result.entry_price == 95000.0
        assert result.stop_loss_price == 93000.0


class TestExecutionTrades:
    def test_list_trades_array_response(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/execution/trades", json=[TRADE_JSON])
        client = _make_client(mock)

        result = client.execution.list_trades()

        assert len(result) == 1
        assert isinstance(result[0], Trade)
        assert result[0].outcome == "win"
        assert result[0].profit_loss == 350.0

    def test_list_trades_with_filters(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/execution/trades", json=[])
        client = _make_client(mock)

        client.execution.list_trades(asset="ETH", outcome="loss")

        params = mock.requests[0].params
        assert params["asset"] == "ETH"
        assert params["outcome"] == "loss"


class TestExecutionEvaluate:
    def test_evaluate_returns_result(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/execution/evaluate/strat-uuid-1", json={
            "success": True,
            "strategy_id": "strat-uuid-1",
            "strategy_name": "BTC Momentum",
            "asset": "BTC-USD",
            "current_price": 97500.0,
            "timestamp": "2026-04-11T12:00:00Z",
            "execution_state": {"cash_balance": 9500, "num_open_positions": 1},
            "new_orders": [
                {"order_id": "ord-1", "side": "entry_long", "price": 97500.0, "status": "filled"},
            ],
            "execution_time_seconds": 2.1,
        })
        client = _make_client(mock)

        result = client.execution.evaluate("strat-uuid-1")

        assert isinstance(result, EvaluateResult)
        assert result.success is True
        assert result.current_price == 97500.0
        assert len(result.new_orders) == 1
        assert mock.requests[0].json == {"persist": True}

    def test_evaluate_no_persist(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/execution/evaluate/strat-uuid-1", json={
            "success": True,
            "new_orders": [],
        })
        client = _make_client(mock)

        client.execution.evaluate("strat-uuid-1", persist=False)

        assert mock.requests[0].json == {"persist": False}
