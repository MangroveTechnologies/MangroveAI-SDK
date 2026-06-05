"""On-chain signals demo — series → signal, end to end, as a normal SDK user.

Walks the full on-chain time-series surface and finishes by feeding a real
series into a `mangrove-kb` on-chain signal to show the complete path:

    Mangrove API  ->  client.on_chain.get_onchain_series(...)  ->  DataFrame
                  ->  mangrove_kb signal  ->  True / False

Sections:
    1. get_onchain_series for every on-chain column (one call, many metrics).
    2. The live trailing-window use case ("last 10 days of smart-money netflow,
       ending now") — the bread-and-butter for real-time strategy evaluation.
    3. Raw per-category flows via get_token_flows(label=...).
    4. A snapshot method (smart-money sentiment) for contrast (point-in-time, not a series).
    5. Assemble an OHLCV-aligned-style DataFrame and evaluate an on-chain signal.

Getting started:
    1. Create an account at https://mangrovedeveloper.ai
    2. Settings > API Keys > Generate a key (starts with `prod_`).
    3. export MANGROVE_API_KEY=prod_your_key_here
       (No env override needed — the SDK defaults to production.)
    4. For section 5: pip install mangrove-kb

Run:
    python examples/onchain_signals_demo.py
"""
from __future__ import annotations

import datetime as dt
import os

from mangrove_ai import MangroveAI

SYMBOL = "WETH"
METRICS = ["SmartMoneyNetflow", "SmartMoneyHoldings", "ExchangeNetflow",
           "WhaleNetInflow", "HolderConcentration"]


def _hdr(title: str) -> None:
    print(f"\n{'=' * 4} {title} {'=' * 4}")


def _today() -> dt.date:
    # Pass dates explicitly so the example is deterministic to read.
    return dt.datetime.now(dt.timezone.utc).date()


def main() -> None:
    if not os.environ.get("MANGROVE_API_KEY"):
        raise SystemExit("Set MANGROVE_API_KEY (a prod_... key) first. See the module docstring.")

    client = MangroveAI()  # env auto-detected from the key prefix; prod by default
    end = _today()
    start_10d = (end - dt.timedelta(days=10)).isoformat()

    # 1. One call, every metric -----------------------------------------------
    _hdr("get_onchain_series — all metrics, last 10 days, hourly")
    series = client.on_chain.get_onchain_series(
        SYMBOL, METRICS, date_from=start_10d, date_to=end.isoformat(), interval="1h",
    )
    print(f"  {series.count} rows | metrics={series.metrics}")
    if series.series:
        last = series.series[-1]
        print(f"  latest bar @ {last['timestamp']}:")
        for m in series.metrics or []:
            print(f"    {m}: {last.get(m)}")

    # 2. Live trailing window — the real-time strategy-eval case ---------------
    _hdr("Live trailing window — last 10 days of smart-money netflow, ending now")
    sm = client.on_chain.get_onchain_series(
        SYMBOL, ["SmartMoneyNetflow"], date_from=start_10d, date_to=end.isoformat(), interval="1h",
    )
    flows = [r["SmartMoneyNetflow"] for r in (sm.series or []) if r.get("SmartMoneyNetflow") is not None]
    if flows:
        print(f"  {len(flows)} hourly net-flow points; window sum = ${sum(flows):,.0f}")

    # 3. Raw per-category flows via the label param ---------------------------
    _hdr("get_token_flows(label=...) — raw hourly rows per wallet category")
    for label in ("smart_money", "exchange", "whale"):
        tf = client.on_chain.get_token_flows(SYMBOL, label=label, date_from=start_10d, date_to=end.isoformat())
        print(f"  label={label:13} -> {tf.count} hourly rows")

    # 4. Snapshot method for contrast (point-in-time, not a series) -----------
    _hdr("Snapshot for contrast — smart-money sentiment (current state)")
    try:
        sent = client.on_chain.get_smart_money_sentiment(SYMBOL)
        print(f"  sentiment={getattr(sent, 'sentiment', None)} score={getattr(sent, 'smart_money_score', None)}")
    except Exception as e:  # snapshot may have no smart-money data for this token right now
        print(f"  (no current sentiment data for {SYMBOL}: {e})")

    # 5. Series -> signal, the full path --------------------------------------
    _hdr("Series -> mangrove-kb signal")
    try:
        import mangrove_kb.signals  # noqa: F401  (registers on-chain signals)
        import pandas as pd
        from mangrove_kb import RuleRegistry
    except ImportError:
        print("  (pip install mangrove-kb pandas to run this section)")
        return

    df = pd.DataFrame(series.series).set_index("timestamp")
    for rule in ("smart_money_net_positive", "whale_net_accumulation", "exchange_net_outflow"):
        decision = RuleRegistry.evaluate({"name": rule, "params": {}}, df)
        print(f"  {rule:28} -> {decision}")


if __name__ == "__main__":
    main()
