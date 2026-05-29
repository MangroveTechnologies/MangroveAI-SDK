"""Oracle experiments quickstart — programmatic sweep authoring.

Walks the full experiment lifecycle:

    1. Discover signals + datasets from the catalog.
    2. Author an experiment config that grids over MACD windows on
       1h BTC OHLCV from 2024.
    3. Validate → launch → poll results.
    4. Cleanup.

The Oracle experiment surface lets you fan out a strategy template
into up to 99 individual backtests per call. Use SIEVE first
(``client.oracle.sieve_score(...)``) to score candidates cheaply,
then send only the most promising ones through a full backtest.

Getting started:
    1. Create an account at https://mangrovedeveloper.ai
    2. Settings > API Keys > Generate a new API key
    3. Set it as an environment variable:
        export MANGROVE_API_KEY=prod_your_key_here

Run:
    python examples/oracle_experiments_quickstart.py
"""
from __future__ import annotations

import time

from mangrove_ai import MangroveAI


def _header(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main() -> None:
    client = MangroveAI()  # reads MANGROVE_API_KEY from environment

    # ----------------------------------------------------------------
    # 1. Discover what the engine can run against.
    # ----------------------------------------------------------------
    _header("1. Catalog — what's available?")
    datasets = client.oracle.list_datasets()
    btc_1h = [d for d in datasets if d["asset"] == "BTC" and d["timeframe"] == "1h"]
    print(f"datasets:  {len(datasets)} total  ({len(btc_1h)} BTC/1h)")
    if btc_1h:
        d = btc_1h[0]
        print(f"  example: {d['file']}  rows={d['rows']}  ({d['start_date']} → {d['end_date']})")

    signals = client.oracle.list_signals()
    momentum_triggers = [s for s in signals if s["category"] == "momentum" and s["type"] == "TRIGGER"]
    print(f"signals:   {len(signals)} total  ({len(momentum_triggers)} momentum triggers)")

    # ----------------------------------------------------------------
    # 2. Author an experiment config.
    # ----------------------------------------------------------------
    _header("2. Create + configure")
    created = client.oracle.create_experiment({
        "name": "BTC 1h MACD momentum sweep (SDK quickstart)",
        "description": "Grid over MACD windows; one entry trigger, one exit trigger.",
        "search_mode": "grid",
        "kind": "single",
        "datasets": [d["file"] for d in btc_1h[:1]],
        "entry_signals": {
            "triggers": [
                {"name": "macd_bullish_cross", "params": {"window_fast": 12, "window_slow": 26}},
            ],
            "filters": [],
            "min_filters": 0,
            "max_filters": 0,
        },
        "exit_signals": {
            "triggers": [
                {"name": "macd_bearish_cross", "params": {"window_fast": 12, "window_slow": 26}},
            ],
            "filters": [],
        },
        "execution_config": {"base": {}, "sweep_axes": []},
    })
    print(f"created:  {created.experiment_id}  status={created.status}")

    cfg = client.oracle.get_experiment(created.experiment_id)
    print(f"name:     {cfg['name']!r}")
    print(f"status:   {cfg['status']}")
    print(f"datasets: {len(cfg.get('datasets', []))} configured")

    # ----------------------------------------------------------------
    # 3. Validate → launch.
    # ----------------------------------------------------------------
    _header("3. Validate + launch")
    try:
        validated = client.oracle.validate_experiment(created.experiment_id)
        print(f"validate: {validated.status}")
        launched = client.oracle.launch_experiment(created.experiment_id)
        print(f"launch:   {launched.status}")
    except Exception as e:
        print(f"engine rejected the launch (config probably incomplete):")
        print(f"  {e}")
        print(f"  → Adjust the config above with `update_experiment(id, cfg)` and retry.")

    # ----------------------------------------------------------------
    # 4. Poll results.
    # ----------------------------------------------------------------
    _header("4. Poll results (5 attempts, 5s apart)")
    for attempt in range(5):
        page = client.oracle.list_results(
            experiment_id=created.experiment_id, limit=10,
        )
        progress = client.oracle.get_experiment(created.experiment_id)
        print(f"  attempt {attempt + 1}:  status={progress.get('status')!s:12s}  "
              f"completed={progress.get('completed_runs', '?')}  "
              f"results_page={len(page.results)}/{page.total}")
        if page.total > 0 or progress.get("status") in {"completed", "failed"}:
            break
        time.sleep(5)

    # ----------------------------------------------------------------
    # 5. Cleanup.
    # ----------------------------------------------------------------
    _header("5. Cleanup")
    deleted = client.oracle.delete_experiment(created.experiment_id)
    print(f"deleted:  {deleted.status}")


if __name__ == "__main__":
    main()
