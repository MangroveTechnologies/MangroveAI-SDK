"""X attention signals demo: post counts to a signal, end to end, as a normal SDK user.

The three x_attention signals read how much people post about an asset on X
(the ``$BTC`` cashtag), not what they say. This example walks the path:

    Mangrove API  ->  client.social.get_x_post_counts(...)  ->  DataFrame (XPostCount)
                  ->  mangrove_kb x_post_count_spike         ->  True / False

Sections:
    1. List the signals in the ``social`` category.
    2. Fetch a week of hourly X post counts for BTC.
    3. Build the XPostCount column and evaluate ``x_post_count_spike`` locally.

The server backfills counts on demand and caches them, so a repeat call for the
same window makes no X request (``x_requests == 0``). In a backtest the engine
reads only buckets that had closed by each bar, so a strategy never sees a
count from its own future.

Getting started:
    1. Create an account at https://mangrovedeveloper.ai
    2. Settings > API Keys > Generate a key (starts with `prod_`).
    3. export MANGROVE_API_KEY=prod_your_key_here
    4. For section 3: pip install pandas "mangrove-kb>=<the release with the X signals>"

Run:
    python examples/x_attention_signals_demo.py
"""
from __future__ import annotations

import os

from mangrove_ai import MangroveAI

SYMBOL = "BTC"


def _hdr(title: str) -> None:
    print(f"\n{'=' * 4} {title} {'=' * 4}")


def main() -> None:
    if not os.environ.get("MANGROVE_API_KEY"):
        raise SystemExit("Set MANGROVE_API_KEY (a prod_... key) first. See the module docstring.")

    client = MangroveAI()

    # 1. The social signal category ----------------------------------------------
    _hdr("signals.list(category='social')")
    page = client.signals.list(category="social", limit=50)
    for s in page.items:
        if s.name.startswith("x_"):
            print(f"  {s.name:32s} {s.signal_type or ''}")

    # 2. Hourly X post counts ----------------------------------------------------
    _hdr(f"get_x_post_counts('{SYMBOL}', days_back=7)")
    counts = client.social.get_x_post_counts(SYMBOL, days_back=7, granularity="hour")
    print(f"  query={counts.query!r} buckets={counts.bucket_count} total_posts={counts.total_posts}")
    print(f"  x_requests={counts.x_requests} (0 means fully cached) buckets_cached={counts.buckets_cached}")
    for b in counts.buckets[-3:]:
        print(f"  {b.start} -> {b.end}: {b.count}")

    # 3. Evaluate a signal locally -----------------------------------------------
    _hdr("x_post_count_spike on the latest closed hour")
    try:
        import mangrove_kb.signals  # noqa: F401  -- registers the signals
        import pandas as pd
        from mangrove_kb.registry import RuleRegistry
    except ImportError:
        RuleRegistry = None
    if RuleRegistry is None or not RuleRegistry.has("x_post_count_spike"):
        print("  Skipped: install pandas and a mangrove-kb release that includes the X signals.")
        return

    df = pd.DataFrame(
        {"XPostCount": [b.count for b in counts.buckets]},
        index=pd.to_datetime([b.end for b in counts.buckets]),
    )
    rule = {"name": "x_post_count_spike", "params": {"window": 48, "z_threshold": 3.0, "min_count": 20}}
    fired = RuleRegistry.evaluate(rule, df)
    print(f"  {len(df)} hours, latest {int(df['XPostCount'].iloc[-1])} posts -> fired={bool(fired)}")


if __name__ == "__main__":
    main()
