"""Cambrian signals demo: one exit signal, six disabled, then a backtest with the exit.

One Cambrian-backed signal is available for new strategies: ``social_price_divergence``
(``social`` category), an EXIT for long positions and never an entry. It fires when close
fell at least ``min_drop_pct`` over ``window`` bars while the crowd's mean net bullish share
(``SocialNetBullShare``, Cambrian Deep42) over the same bars stayed at or above its mean over
the ``window_baseline`` readings before them. True means exit the long. Defaults: window=7,
min_drop_pct=3.0, window_baseline=60.

Six other Cambrian signals are disabled for new strategies until they are validated in
strategy backtests across market regimes (stored strategies keep evaluating them):
social_sentiment_surge, social_sentiment_capitulation, social_crowd_bullish,
social_crowd_cooling, whale_share_divergence, holder_growth_trend.

This example needs no Cambrian data on your side. The server attaches the columns the signal
reads, in live evaluation and in backtests, so the strategy below is built and backtested
through the same SDK methods as any other.

Sections:
    1. List the Cambrian signals and the status the server reports for each.
    2. Read ``social_price_divergence``: the columns it requires and its parameters.
    3. Build a strategy that enters on an ``rsi_cross_up`` trigger with an ``is_above_sma``
       price filter and exits on ``social_price_divergence``, then backtest it.

Notes:
    * ``social_price_divergence`` is typed TRIGGER because the knowledge base has no
      exit-only type. Put it in ``exit`` only.
    * A bar sees only values already known when the bar closes, in a backtest as in live
      evaluation. Deep42 buckets are daily, so the demo uses daily bars.
    * The server attaches Cambrian columns only when its Cambrian data flag is on, and this
      requires a MangroveAI release that is not yet deployed. With the flag off the catalogue
      marks the signal non-composable and section 3 is skipped.
    * The catalogue reports the disabled status of the six, and the exit defaults above, from a
      knowledge-base release that the server does not yet pin.

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

EXIT_SIGNAL = "social_price_divergence"

# The Cambrian-backed signals, by category. Only EXIT_SIGNAL is meant for new strategies.
CAMBRIAN_SIGNALS = {
    "social": [
        "social_price_divergence",
        "social_sentiment_surge",
        "social_sentiment_capitulation",
        "social_crowd_bullish",
        "social_crowd_cooling",
    ],
    "onchain": [
        "whale_share_divergence",
        "holder_growth_trend",
    ],
}


def _hdr(title: str) -> None:
    print(f"\n{'=' * 4} {title} {'=' * 4}")


def main() -> None:
    if not os.environ.get("MANGROVE_API_KEY"):
        raise SystemExit("Set MANGROVE_API_KEY (a prod_... key) first. See the module docstring.")

    client = MangroveAI()  # env auto-detected from the key prefix; prod by default

    # 1. The Cambrian signals and their status ------------------------------------
    _hdr("signals.list(category=...) -- the Cambrian-backed signals")
    exit_composable = False
    for category, names in CAMBRIAN_SIGNALS.items():
        by_name = {s.name: s for s in client.signals.list_iter(category=category)}
        print(f"  category={category}")
        for name in names:
            s = by_name.get(name)
            if s is None:
                print(f"    {name:32s} not listed by this server")
                continue
            # The server reports these top-level fields; the SDK model keeps them as extras.
            composable = getattr(s, "composable", True) is not False
            status = getattr(s, "status", None) or ("active" if composable else "disabled")
            print(f"    {name:32s} {s.signal_type or '':8s} status={status}")
            if not composable:
                print(f"      non-composable: {getattr(s, 'reason', None)}")
            if name == EXIT_SIGNAL:
                exit_composable = composable

    # 2. The exit signal's metadata -----------------------------------------------
    _hdr(f"signals.get({EXIT_SIGNAL!r})")
    sig = client.signals.get(EXIT_SIGNAL)
    meta = sig.metadata
    print(f"  {meta.description if meta else ''}")
    print(f"  requires: {', '.join((meta.requires if meta else None) or [])}")
    print(f"  params: {meta.params if meta else None}")

    if not exit_composable:
        print(f"\n  Skipping the strategy: {EXIT_SIGNAL} is missing or non-composable on this server.")
        client.close()
        return

    # 3. Price trigger + price filter, with social_price_divergence as the exit ----
    _hdr(f"Strategy: rsi_cross_up + is_above_sma, exit on {EXIT_SIGNAL}, on {SYMBOL}")
    entry = [
        {"name": "rsi_cross_up", "signal_type": "TRIGGER", "timeframe": "1d",
         "params": {"window": 14, "threshold": 50}},
        {"name": "is_above_sma", "signal_type": "FILTER", "timeframe": "1d",
         "params": {"window": 60}},
    ]
    exit_rules = [
        # Exit a long when price fell at least 3% over 7 days while the crowd's net bullish
        # share stayed at or above its prior 60-day mean.
        {"name": EXIT_SIGNAL, "signal_type": "TRIGGER", "timeframe": "1d",
         "params": {"window": 7, "min_drop_pct": 3.0, "window_baseline": 60}},
    ]
    strategy = client.strategies.create(CreateStrategyRequest(
        name="SDK Demo - RSI cross up, exit when the crowd ignores a drop",
        asset=SYMBOL,
        description=("Enters on an RSI cross above 50 while price is above its 60-day SMA; exits a "
                     "long when price falls 3% over 7 days while the crowd stays bullish"),
        entry=entry,
        exit=exit_rules,
        reward_factor=2.0,
    ))
    print(f"  created strategy {strategy.name} (id={strategy.id})")

    try:
        # The exit needs 66 daily readings of warmup (window + window_baseline - 1),
        # so look back far enough to leave bars to trade after it.
        result = client.backtesting.run(BacktestRequest(
            asset=SYMBOL,
            interval="1d",
            strategy_json=json.dumps({
                "name": strategy.name,
                "asset": SYMBOL,
                "entry": entry,
                "exit": exit_rules,
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
                print("  No trades: the RSI trigger and the SMA filter never agreed in this window.")
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
