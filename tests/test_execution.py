from __future__ import annotations

import pytest

from mangrove_ai import MangroveAI
from mangrove_ai._transport._mock import MockTransport
from mangrove_ai.models.execution import (
    Account,
    CreateAccountRequest,
    EvaluateResult,
    ExternalExecutionRequest,
    Position,
    Trade,
)


def _make_client(mock: MockTransport) -> MangroveAI:
    return MangroveAI(api_key="test_abc123", environment="local", httpx_client=mock)


def test_pause_payment_replacement_preserves_command_identity():
    from uuid import uuid4
    mock = MockTransport()
    mock.add_response('POST', '/pause', json={'state': 'paused'})
    client = _make_client(mock)
    strategy, controller, command, payment = (str(uuid4()) for _ in range(4))
    client.execution.paper_pause(strategy, controller_id=controller, request_id=command)
    client.execution.paper_pause(strategy, controller_id=controller, request_id=command, payment_operation_id=payment)
    assert mock.requests[0].json == mock.requests[1].json
    assert mock.requests[0].headers['X-Payment-Operation-Id'] == command
    assert mock.requests[1].headers['X-Payment-Operation-Id'] == payment


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

    def test_update_account_fails_before_request(self) -> None:
        from mangrove_ai import NotImplementedLayerError
        mock = MockTransport()
        with pytest.raises(NotImplementedLayerError, match="not supported"):
            _make_client(mock).execution.update_account("acct-uuid-1", name="Renamed")
        assert mock.requests == []


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
        assert params["open_only"] == "true"
        assert "status" not in params

    def test_get_position_fails_before_request(self) -> None:
        from mangrove_ai import NotImplementedLayerError
        mock = MockTransport()
        with pytest.raises(NotImplementedLayerError, match="no position-detail"):
            _make_client(mock).execution.get_position("pos-uuid-1")
        assert mock.requests == []

    def test_closed_filter_uses_all_positions_then_filters_the_server_page(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/execution/positions", json=[
            POSITION_JSON, {**POSITION_JSON, "id": "closed-1", "open": False},
        ])
        positions = _make_client(mock).execution.list_positions(
            status="closed", strategy_id="s1", asset="BTC", skip=10, limit=20,
        )
        assert [position.id for position in positions] == ["closed-1"]
        assert mock.requests[0].params == {
            "skip": 10, "limit": 20, "open_only": "false", "strategy_id": "s1", "asset": "BTC",
        }

    def test_open_only_false_returns_both_open_and_closed(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/execution/positions", json=[
            POSITION_JSON, {**POSITION_JSON, "id": "closed-1", "open": False},
        ])
        positions = _make_client(mock).execution.list_positions(open_only=False)
        assert [position.open for position in positions] == [True, False]

    def test_contradictory_filters_do_not_make_a_request(self) -> None:
        from mangrove_ai import ConfigurationError
        mock = MockTransport()
        with pytest.raises(ConfigurationError, match="conflicting"):
            _make_client(mock).execution.list_positions(status="closed", open_only=True)
        assert mock.requests == []


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


# =============================================================================
# evaluate_by_object
# =============================================================================


class TestExecutionEvaluateByObject:
    def test_evaluate_by_object_posts_strategy_dict(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/execution/evaluate", json={
            "success": True,
            "asset": "ETH-USD",
            "current_price": 3500.0,
            "new_orders": [],
            "execution_time_seconds": 0.8,
        })
        client = _make_client(mock)

        strategy = {
            "asset": "ETH-USD",
            "rules": {"entry": [{"name": "macd_bullish_cross"}], "exit": []},
            "execution_config": {"timeframe": "1h"},
            "execution_state": {
                "cash_balance": 10000,
                "account_value": 10000,
                "total_trades": 0,
                "num_open_positions": 0,
            },
        }
        result = client.execution.evaluate_by_object(strategy)

        from mangrove_ai.models.execution import EvaluateResult
        assert isinstance(result, EvaluateResult)
        assert result.asset == "ETH-USD"
        recorded = mock.requests[-1]
        assert recorded.json == {"strategy": strategy, "persist": False}

    def test_evaluate_by_object_persist_opt_in(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/execution/evaluate", json={"success": True})
        client = _make_client(mock)

        client.execution.evaluate_by_object({"asset": "BTC"}, persist=True)

        assert mock.requests[-1].json == {"strategy": {"asset": "BTC"}, "persist": True}

    def test_evaluate_by_object_round_trips_open_positions(self) -> None:
        """Caller-owned positions remain separate from proposed fills."""
        position = {
            "id": "pos-1",
            "asset": "ETH-USD",
            "entry_price": 1800.0,
            "position_size": 0.5,
            "open": True,
            "orders": [
                {"id": "o-1", "asset": "ETH-USD", "order_type": "stop_loss",
                 "side": "exit_long", "status": "pending", "price": 1750.0,
                 "position_size": 0.5, "position_id": "pos-1", "history": {}},
            ],
        }
        updated = [dict(position, entry_price=1800.0)]
        mock = MockTransport()
        mock.add_response("POST", "/execution/evaluate", json={
            "success": True,
            "new_orders": [],
            "open_positions": updated,
        })
        client = _make_client(mock)

        result = client.execution.evaluate_by_object(
            {"asset": "ETH-USD"}, open_positions=[position],
        )

        assert mock.requests[-1].json == {
            "strategy": {"asset": "ETH-USD"},
            "persist": False,
            "open_positions": [position],
        }
        assert result.open_positions == updated

    def test_evaluate_by_object_omits_open_positions_when_none(self) -> None:
        """Default calls stay byte-identical to the pre-#40 wire shape."""
        mock = MockTransport()
        mock.add_response("POST", "/execution/evaluate", json={"success": True})
        client = _make_client(mock)

        result = client.execution.evaluate_by_object({"asset": "BTC"})

        assert "open_positions" not in mock.requests[-1].json
        assert result.open_positions is None

    def test_evaluate_by_object_sends_typed_external_execution_v2(self) -> None:
        opened = {
            "kind": "opened",
            "sequence": 1,
            "event_id": "evt-open-1",
            "position_id": "pos-1",
            "asset": "XLM-USD",
            "filled_quantity": "1.2500",
            "occurred_at": None,
        }
        closed = {
            "kind": "closed",
            "sequence": 2,
            "event_id": "evt-close-1",
            "position_id": "pos-1",
            "asset": "XLM-USD",
            "realized_pnl": "-0.1250",
            "fees": "0.0025",
            "occurred_at": "2026-10-16T15:30:00Z",
        }
        batch = ExternalExecutionRequest(
            observed_at="2026-10-16T15:31:00Z",
            events=[opened, closed],
        )
        mock = MockTransport()
        mock.add_response("POST", "/execution/evaluate", json={"success": True})
        client = _make_client(mock)

        client.execution.evaluate_by_object({"asset": "XLM-USD"}, external_execution=batch)

        assert mock.requests[-1].json == {
            "strategy": {"asset": "XLM-USD"},
            "persist": False,
            "external_execution": {
                "contract_version": 2,
                "observed_at": "2026-10-16T15:31:00Z",
                "events": [opened, closed],
            },
        }

    def test_evaluate_by_object_accepts_external_execution_mapping(self) -> None:
        batch = {
            "contract_version": 2,
            "observed_at": "2026-10-16T15:31:00Z",
            "events": [{
                "kind": "opened",
                "sequence": 1,
                "event_id": "evt-open-1",
                "position_id": "pos-1",
                "asset": "XLM-USD",
                "filled_quantity": "1.25",
                "occurred_at": None,
            }],
        }
        mock = MockTransport()
        mock.add_response("POST", "/execution/evaluate", json={"success": True})
        client = _make_client(mock)

        client.execution.evaluate_by_object({"asset": "XLM-USD"}, external_execution=batch)

        assert mock.requests[-1].json["external_execution"] == batch

    @pytest.mark.parametrize("event,match", [
        ({"kind": "opened", "sequence": True, "event_id": "e", "position_id": "p",
          "asset": "X", "filled_quantity": "1", "occurred_at": None}, "sequence"),
        ({"kind": "opened", "sequence": 1, "event_id": "e", "position_id": "p",
          "asset": "X", "filled_quantity": "0", "occurred_at": None}, "filled_quantity"),
        ({"kind": "opened", "sequence": 1, "event_id": "e", "position_id": "p",
          "asset": "X", "filled_quantity": "NaN", "occurred_at": None}, "exact decimal"),
        ({"kind": "closed", "sequence": 1, "event_id": "e", "position_id": "p",
          "asset": "X", "realized_pnl": "Infinity", "fees": "0", "occurred_at": None}, "exact decimal"),
        ({"kind": "closed", "sequence": 1, "event_id": "e", "position_id": "p",
          "asset": "X", "realized_pnl": "1", "fees": "-0.01", "occurred_at": None}, "fees"),
    ])
    def test_external_execution_request_rejects_invalid_event_values(self, event, match) -> None:
        with pytest.raises(ValueError, match=match):
            ExternalExecutionRequest(
                observed_at="2026-10-16T15:31:00Z",
                events=[event],
            )

    def test_external_execution_request_rejects_bool_version_and_late_event_time(self) -> None:
        event = {
            "kind": "opened",
            "sequence": 1,
            "event_id": "evt-open-1",
            "position_id": "pos-1",
            "asset": "XLM-USD",
            "filled_quantity": "1",
            "occurred_at": "2026-10-16T15:32:00Z",
        }
        with pytest.raises(ValueError, match="contract_version"):
            ExternalExecutionRequest(
                contract_version=True,
                observed_at="2026-10-16T15:31:00Z",
                events=[{**event, "occurred_at": None}],
            )
        with pytest.raises(ValueError, match="contract_version"):
            ExternalExecutionRequest(
                contract_version=2.0,
                observed_at="2026-10-16T15:31:00Z",
                events=[{**event, "occurred_at": None}],
            )
        with pytest.raises(ValueError, match="occurred_at cannot be after observed_at"):
            ExternalExecutionRequest(
                observed_at="2026-10-16T15:31:00Z",
                events=[event],
            )

    def test_external_execution_request_matches_hosted_batch_limit_and_zero_fee_canonicalization(self) -> None:
        closed = {
            "kind": "closed", "sequence": 1, "event_id": "e1", "position_id": "p1",
            "asset": "XLM-USD", "realized_pnl": "0", "fees": "-0.000", "occurred_at": None,
        }
        accepted = ExternalExecutionRequest(
            observed_at="2026-10-16T15:31:00Z",
            events=[closed],
        )
        assert accepted.events[0].fees == "-0.000"

        opened = {
            "kind": "opened", "event_id": "e", "position_id": "p", "asset": "XLM-USD",
            "filled_quantity": "1", "occurred_at": None,
        }
        with pytest.raises(ValueError, match="at most 512"):
            ExternalExecutionRequest(
                observed_at="2026-10-16T15:31:00Z",
                events=[{**opened, "sequence": index + 1} for index in range(513)],
            )

    def test_external_execution_request_requires_events_in_sequence_order(self) -> None:
        first = {
            "kind": "opened", "sequence": 2, "event_id": "e2", "position_id": "p2",
            "asset": "XLM-USD", "filled_quantity": "1", "occurred_at": None,
        }
        second = {
            "kind": "closed", "sequence": 1, "event_id": "e1", "position_id": "p1",
            "asset": "XLM-USD", "realized_pnl": "0", "fees": "0", "occurred_at": None,
        }
        with pytest.raises(ValueError, match="strictly increasing"):
            ExternalExecutionRequest(
                observed_at="2026-10-16T15:31:00Z",
                events=[first, second],
            )

    def test_evaluate_result_preserves_typed_external_execution_ack_and_legacy_shape(self) -> None:
        ack = {
            "contract_version": 2,
            "applied_through": 2,
            "receipts": [{
                "sequence": 2,
                "event_id": "evt-close-1",
                "position_id": "pos-1",
                "kind": "closed",
                "sha256": "a" * 64,
                "occurred_at": None,
                "accounting_at": "2026-10-16T15:31:00Z",
            }],
            "active_position_ids": [],
            "last_observed_at": "2026-10-16T15:31:00Z",
        }
        mock = MockTransport()
        mock.add_response("POST", "/execution/evaluate", json={
            "success": True,
            "execution_state": {"cash_balance": 999.0, "external_execution": ack},
        })
        client = _make_client(mock)
        result = client.execution.evaluate_by_object({"asset": "XLM-USD"})

        assert result.external_execution_ack is not None
        assert result.external_execution_ack.applied_through == 2
        assert result.external_execution_ack.receipts[0].event_id == "evt-close-1"
        assert result.execution_state["external_execution"] == ack
        assert result.model_dump()["execution_state"]["external_execution"] == ack
        legacy = EvaluateResult.model_validate({"success": True, "execution_state": {"cash_balance": 10}})
        assert legacy.external_execution_ack is None
        future_ack = {"contract_version": 3, "cursor": 4, "future_receipts": ["opaque"]}
        future = EvaluateResult.model_validate({
            "success": True,
            "execution_state": {"external_execution": future_ack},
        })
        assert future.external_execution_ack is None
        assert future.model_dump()["execution_state"]["external_execution"] == future_ack

    def test_evaluate_result_exposes_v2_position_templates_and_disposition(self) -> None:
        template = {"position_id": "model-1", "asset": "XLM-USD", "quantity": 1.25}
        mock = MockTransport()
        mock.add_response("POST", "/execution/evaluate", json={
            "success": True,
            "position_templates": [template],
            "external_execution_disposition": "duplicate_bar",
            "open_positions": [{"position_id": "broker-1", "asset": "XLM-USD"}],
        })
        client = _make_client(mock)

        result = client.execution.evaluate_by_object({"asset": "XLM-USD"})

        assert result.position_templates == [template]
        assert result.external_execution_disposition == "duplicate_bar"
        assert result.open_positions == [{"position_id": "broker-1", "asset": "XLM-USD"}]


# =============================================================================
# evaluate_bulk
# =============================================================================


class TestExecutionEvaluateBulk:
    def test_evaluate_bulk_with_ids(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/execution/evaluate/bulk", json={
            "success": True,
            "results": [
                {
                    "success": True,
                    "strategy_id": "s-1",
                    "strategy_name": "BTC momentum",
                    "asset": "BTC-USD",
                    "current_price": 97500.0,
                    "new_orders": [],
                    "execution_time_seconds": 1.0,
                },
                {
                    "success": True,
                    "strategy_id": "s-2",
                    "strategy_name": "ETH momentum",
                    "asset": "ETH-USD",
                    "current_price": 3500.0,
                    "new_orders": [],
                    "execution_time_seconds": 1.0,
                },
            ],
            "data_fetches": 2,
            "total_execution_time_seconds": 1.5,
        })
        client = _make_client(mock)

        result = client.execution.evaluate_bulk(strategy_ids=["s-1", "s-2"])

        from mangrove_ai.models.execution import BulkEvaluateResult
        assert isinstance(result, BulkEvaluateResult)
        assert len(result.results) == 2
        assert result.data_fetches == 2
        assert mock.requests[-1].json == {
            "persist": False,
            "strategy_ids": ["s-1", "s-2"],
        }

    def test_evaluate_bulk_captures_per_strategy_failures(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/execution/evaluate/bulk", json={
            "success": True,
            "results": [
                {"success": True, "strategy_id": "s-1", "new_orders": []},
                {"success": False, "strategy_id": "s-2", "error": "stale OHLCV"},
            ],
            "data_fetches": 1,
            "total_execution_time_seconds": 1.0,
        })
        client = _make_client(mock)

        result = client.execution.evaluate_bulk(strategy_ids=["s-1", "s-2"])

        assert result.success is True
        assert result.results[0].success is True
        assert result.results[1].success is False
        assert result.results[1].error == "stale OHLCV"

    def test_evaluate_bulk_inline_configs(self) -> None:
        mock = MockTransport()
        mock.add_response("POST", "/execution/evaluate/bulk", json={
            "success": True,
            "results": [],
            "data_fetches": 0,
            "total_execution_time_seconds": 0.0,
        })
        client = _make_client(mock)

        configs = [{"asset": "BTC", "rules": {}, "execution_config": {}, "execution_state": {}}]
        client.execution.evaluate_bulk(strategy_configs=configs)

        body = mock.requests[-1].json
        assert body == {"persist": False, "strategy_configs": configs}
        assert "strategy_ids" not in body

    def test_evaluate_bulk_rejects_empty_request(self) -> None:
        import pytest
        client = _make_client(MockTransport())

        with pytest.raises(ValueError, match="strategy_ids.*strategy_configs"):
            client.execution.evaluate_bulk()


# =============================================================================
# get_portfolio
# =============================================================================


class TestExecutionGetPortfolio:
    def test_get_portfolio_returns_typed_response(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/execution/portfolio", json={
            "results": [
                {
                    "strategy_id": "s-1",
                    "strategy_name": "BTC Momentum",
                    "asset": "BTC-USD",
                    "status": "paper",
                    "execution_state": {"cash_balance": 9500.0, "total_trades": 3},
                    "last_evaluated_at": "2026-05-29T10:00:00Z",
                    "open_positions_count": 1,
                    "recent_trades": [
                        {
                            "id": "tr-1",
                            "asset": "BTC-USD",
                            "outcome": "win",
                            "profit_loss": 120.0,
                            "profit_loss_pct": 1.2,
                            "closed_at": "2026-05-29T09:00:00Z",
                        }
                    ],
                }
            ],
            "missing": ["s-deleted"],
        })
        client = _make_client(mock)

        result = client.execution.get_portfolio(["s-1", "s-deleted"])

        from mangrove_ai.models.execution import PortfolioResponse
        assert isinstance(result, PortfolioResponse)
        assert len(result.results) == 1
        assert result.results[0].strategy_id == "s-1"
        assert result.results[0].open_positions_count == 1
        assert len(result.results[0].recent_trades) == 1
        assert result.missing == ["s-deleted"]

    def test_get_portfolio_serializes_ids_as_csv(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/execution/portfolio", json={"results": [], "missing": []})
        client = _make_client(mock)

        client.execution.get_portfolio(["a", "b", "c"])

        assert mock.requests[-1].params == {"strategy_ids": "a,b,c"}

    def test_get_portfolio_rejects_empty(self) -> None:
        import pytest
        client = _make_client(MockTransport())

        with pytest.raises(ValueError, match="non-empty"):
            client.execution.get_portfolio([])

    def test_get_portfolio_rejects_over_100(self) -> None:
        import pytest
        client = _make_client(MockTransport())

        with pytest.raises(ValueError, match="Max 100"):
            client.execution.get_portfolio([f"s-{i}" for i in range(101)])


def test_paper_tick_has_stable_payment_operation_identity():
    from uuid import uuid4
    sid, run, controller = (str(uuid4()) for _ in range(3))
    mock = MockTransport()
    for _ in range(3):
        mock.add_response("POST", f"/execution/paper/{sid}/tick", json={"success": True})
    client = _make_client(mock)
    for slot in (10,10,11):
        assert client.execution.paper_tick(sid, controller_id=controller, run_id=run, slot=slot)["success"]
    ids = [request.headers["X-Payment-Operation-Id"] for request in mock.requests]
    assert ids[0] == ids[1]
    assert ids[1] != ids[2]


@pytest.mark.parametrize("bulk", [False, True])
def test_confirmed_history_and_proposals_remain_separate(bulk: bool) -> None:
    """Single and bulk preserve the actual close ledger, never substituting proposals."""
    close = {"position_id": "confirmed-1", "exit_timestamp": "2026-10-29T10:00:00Z",
             "booked_at": "2026-10-29T10:01:00Z", "realized_pnl": -7.0}
    strategy = {"asset": "ETH", "closed_positions": [close],
                "closed_positions_bootstrap_complete": True}
    response = {
        "success": True,
        "execution_state": {"risk_state": {"recent_close_ids": ["confirmed-1"]}},
        "open_positions": [],
        "closed_trades": [],
        "proposed_closes": [{"position_id": "pending-1", "profit_loss": 5.0,
                             "execution_confirmed": False}],
        "proposed_positions": [{"id": "entry-1", "open": False,
                                "execution_confirmed": False, "orders": [{"id": "bracket-1"}]}],
    }
    mock = MockTransport()
    mock.add_response("POST", "/execution/evaluate/bulk" if bulk else "/execution/evaluate",
                      json={"success": True, "results": [response]} if bulk else response)
    client = _make_client(mock)
    if bulk:
        result = client.execution.evaluate_bulk(
            strategy_configs=[{**strategy, "open_positions": []}],
        ).results[0]
        sent = mock.requests[-1].json["strategy_configs"][0]
        assert sent["open_positions"] == []
    else:
        result = client.execution.evaluate_by_object(strategy, open_positions=[])
        sent = mock.requests[-1].json["strategy"]
        assert mock.requests[-1].json["open_positions"] == []
    assert sent["closed_positions"] == [close]
    assert sent["closed_positions_bootstrap_complete"] is True
    assert "closed_positions" not in mock.requests[-1].json
    assert "open_positions" not in strategy
    assert result.open_positions == []
    assert result.closed_trades == []
    assert result.proposed_closes == response["proposed_closes"]
    assert result.proposed_positions == response["proposed_positions"]
    assert result.execution_state["risk_state"]["recent_close_ids"] == ["confirmed-1"]
    assert result.model_dump(exclude_none=True) == response
