"""Bulk strategy evaluation + portfolio snapshot quickstart.

Demonstrates the three execution-gap methods added in this release:

    - evaluate_bulk(strategy_ids=[...])  -- evaluate N strategies in
      one HTTP call with shared market-data fetches. Replaces the
      N+1 loop over evaluate(id).
    - evaluate_by_object(strategy_dict)  -- evaluate a draft strategy
      WITHOUT first persisting it to MangroveAI. Useful for dry runs
      and parameter exploration.
    - get_portfolio(strategy_ids=[...])  -- batched dashboard snapshot:
      name + asset + status + execution_state + open positions + last
      5 trades, per strategy.

Getting started:
    1. Create an account at https://mangrovedeveloper.ai
    2. Settings > API Keys > Generate a new API key
    3. Set it as an environment variable:
        export MANGROVE_API_KEY=prod_your_key_here

Run:
    python examples/execution_bulk_quickstart.py
"""
from __future__ import annotations

from mangrove_ai import MangroveAI


def _header(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main() -> None:
    client = MangroveAI()  # reads MANGROVE_API_KEY from environment

    # ----------------------------------------------------------------
    # 1. Find some strategies to work with. List the first few.
    # ----------------------------------------------------------------
    _header("1. Find some strategies to work with")
    page = client.strategies.list(limit=5)
    if not page.items:
        print("No strategies on this account — create some via the UI or")
        print("client.strategies.create(...) before running this example.")
        return
    strategy_ids = [s.id for s in page.items]
    print(f"Working with {len(strategy_ids)} strategies:")
    for s in page.items:
        print(f"  {s.id}  {s.name!r}  ({s.asset}, {s.status})")

    # ----------------------------------------------------------------
    # 2. Bulk evaluation: one HTTP call, shared market-data fetches.
    # ----------------------------------------------------------------
    _header("2. evaluate_bulk — one HTTP call, shared market-data fetches")
    bulk = client.execution.evaluate_bulk(strategy_ids=strategy_ids, persist=False)
    print(f"success:                 {bulk.success}")
    print(f"data_fetches:            {bulk.data_fetches}   "
          f"(vs {len(strategy_ids)} individual calls)")
    print(f"total_execution_seconds: {bulk.total_execution_time_seconds:.2f}")
    print()
    for r in bulk.results:
        if r.success:
            order_count = len(r.new_orders or [])
            print(f"  ✓ {r.strategy_id}  {r.strategy_name!r}  "
                  f"{r.asset}@{r.current_price}  new_orders={order_count}")
        else:
            print(f"  ✗ {r.strategy_id}  error={r.error!r}")

    # ----------------------------------------------------------------
    # 3. Portfolio snapshot: dashboard-ready data for the same N
    #    strategies in one batched read.
    # ----------------------------------------------------------------
    _header("3. get_portfolio — dashboard snapshot, batched")
    portfolio = client.execution.get_portfolio(strategy_ids)
    print(f"found:   {len(portfolio.results)}")
    print(f"missing: {portfolio.missing}")
    print()
    for entry in portfolio.results:
        state = entry.execution_state or {}
        print(f"  {entry.strategy_name!r:35s}  {entry.asset!s:8s}  "
              f"status={entry.status!s:8s}  "
              f"open={entry.open_positions_count}  "
              f"trades={state.get('total_trades', '?')}")
        for trade in entry.recent_trades[:3]:
            print(f"      └─ {trade.closed_at}  {trade.outcome}  "
                  f"P&L=${trade.profit_loss:+.2f}")

    # ----------------------------------------------------------------
    # 4. evaluate_by_object — dry-run a draft strategy WITHOUT saving
    #    it. Useful when exploring parameters before committing.
    # ----------------------------------------------------------------
    _header("4. evaluate_by_object — dry-run without persisting")
    draft = {
        "name": "ETH 1h MACD dry-run",
        "asset": "ETH-USD",
        "rules": {
            "entry": [
                {
                    "name": "macd_bullish_cross",
                    "signal_type": "TRIGGER",
                    "timeframe": "1h",
                    "params": {"window_fast": 12, "window_slow": 26, "window_sign": 9},
                }
            ],
            "exit": [
                {
                    "name": "macd_bearish_cross",
                    "signal_type": "TRIGGER",
                    "timeframe": "1h",
                    "params": {"window_fast": 12, "window_slow": 26, "window_sign": 9},
                }
            ],
        },
        "execution_config": {"timeframe": "1h"},
        "execution_state": {
            "cash_balance": 10_000.0,
            "account_value": 10_000.0,
            "total_trades": 0,
            "num_open_positions": 0,
        },
    }
    dry = client.execution.evaluate_by_object(draft, persist=False)
    print(f"success:        {dry.success}")
    print(f"asset:          {dry.asset}")
    print(f"current_price:  {dry.current_price}")
    print(f"new_orders:     {len(dry.new_orders or [])}")
    if dry.error:
        print(f"error:          {dry.error}")


if __name__ == "__main__":
    main()
