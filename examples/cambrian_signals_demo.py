"""Cambrian social and holder signals demo: discover the signals, then backtest one.

Six signals read Cambrian data: four in the ``social`` category (Deep42 sentiment) and
two in the ``onchain`` category (Solana holder distribution). This example needs no
Cambrian data on your side. The server attaches the columns the signals read, in live
evaluation and in backtests, so the strategy below is built and backtested through the
same SDK methods as any other.

Sections:
    1. List the six signals by category (``social`` and ``onchain``).
    2. Read one signal's metadata: the columns it requires and its parameters.
    3. Build a strategy that enters on an RSI trigger and uses ``social_crowd_bullish``
       as a FILTER, then backtest it.

Notes:
    * The holder signals (``holder_growth_trend``, ``whale_share_divergence``) work on
      Solana tokens only. ``social_crowd_bullish`` reads Deep42 sentiment, so pick an
      asset Deep42 covers. Change ``SYMBOL`` if your asset is not covered.
    * A bar sees only values already known when the bar closes, in a backtest as in
      live evaluation. Deep42 buckets are daily, so the demo uses daily bars.
    * If the server's Cambrian data source is off, the catalogue marks the six signals
      non-composable and a strategy built on them never fires. Section 3 then reports
      zero trades.

Getting started:
    1. Create an account at https://mangrovedeveloper.ai
    2. Settings > API Keys > Generate a key (starts with `prod_`).
    3. export MANGROVE_API_KEY=prod_your_key_here

Run:
    python examples/cambrian_signals_demo.py
"""
from __future__ import annotations

import json
import os

from mangrove_ai import MangroveAI
from mangrove_ai.models import BacktestRequest, CreateStrategyRequest

SYMBOL = "BTC"

# The six Cambrian-backed signals, by category.
CAMBRIAN_SIGNALS = {
    "social": [
        "social_sentiment_surge",
        "social_sentiment_capitulation",
        "social_crowd_bullish",
        "social_price_divergence",
    ],
    "onchain": [
        "holder_growth_trend",
        "whale_share_divergence",
    ],
}


def _hdr(title: str) -> None:
    print(f"\n{'=' * 4} {title} {'=' * 4}")


def main() -> None:
    if not os.environ.get("MANGROVE_API_KEY"):
        raise SystemExit("Set MANGROVE_API_KEY (a prod_... key) first. See the module docstring.")

    client = MangroveAI()  # env auto-detected from the key prefix; prod by default

    # 1. The six signals, by category ----------------------------------------------
    _hdr("signals.list(category=...) -- the Cambrian-backed signals")
    composable = True
    for category, names in CAMBRIAN_SIGNALS.items():
        by_name = {s.name: s for s in client.signals.list_iter(category=category)}
        print(f"  category={category}")
        for name in names:
            s = by_name.get(name)
            if s is None:
                print(f"    {name:32s} not listed by this server")
                composable = False
                continue
            requires = ", ".join((s.metadata.requires if s.metadata else None) or [])
            print(f"    {name:32s} {s.signal_type or '':8s} requires: {requires}")
            # Reported by the server when it marks a signal non-composable.
            if getattr(s, "composable", True) is False:
                composable = False
                print(f"      non-composable: {getattr(s, 'reason', None)}")

    # 2. One signal's metadata -----------------------------------------------------
    _hdr("signals.get('social_crowd_bullish')")
    crowd = client.signals.get("social_crowd_bullish")
    print(f"  {crowd.metadata.description if crowd.metadata else ''}")
    print(f"  params: {crowd.metadata.params if crowd.metadata else None}")

    if not composable:
        print("\n  Skipping the strategy: a signal above is missing or non-composable on this server.")
        client.close()
        return

    # 3. Build and backtest a strategy with social_crowd_bullish as a filter -------
    _hdr(f"Strategy: RSI oversold trigger + social_crowd_bullish filter on {SYMBOL}")
    entry = [
        {"name": "rsi_oversold", "signal_type": "TRIGGER", "timeframe": "1d",
         "params": {"window": 14, "threshold": 30}},
        {"name": "social_crowd_bullish", "signal_type": "FILTER", "timeframe": "1d",
         "params": {"window": 7, "window_baseline": 60, "margin": 0.0}},
    ]
    strategy = client.strategies.create(CreateStrategyRequest(
        name="SDK Demo - RSI dip with bullish crowd",
        asset=SYMBOL,
        description="Buys an RSI oversold dip only while recent posts lean more bullish than the asset's norm",
        entry=entry,
        exit=[],
        reward_factor=2.0,
    ))
    print(f"  created strategy {strategy.name} (id={strategy.id})")

    try:
        # The filter needs 66 daily readings of warmup (window + window_baseline - 1),
        # so look back far enough to leave bars to trade after it.
        result = client.backtesting.run(BacktestRequest(
            asset=SYMBOL,
            interval="1d",
            strategy_json=json.dumps({
                "name": strategy.name,
                "asset": SYMBOL,
                "entry": entry,
                "exit": [],
            }),
            lookback_months=12,
            initial_balance=10000,
        ))
        if result.success:
            print(f"  backtest: {result.trade_count} trades")
            for key in ("total_return", "sharpe_ratio", "max_drawdown", "win_rate"):
                value = (result.metrics or {}).get(key)
                if value is not None:
                    print(f"    {key}: {value}")
            if not result.trade_count:
                print("  No trades. Either the filter never agreed with an RSI dip in this window, or the")
                print("  server has no Cambrian data for this asset and the filter returned False throughout.")
        else:
            print(f"  backtest failed: {result.error}")
    finally:
        try:
            client.strategies.delete(strategy.id)
            print(f"  cleaned up strategy {strategy.id}")
        except Exception as e:  # deleting may need the strategy:delete permission
            print(f"  could not delete strategy: {e}")

    client.close()


if __name__ == "__main__":
    main()
