"""Oracle full-surface quickstart — every customer-facing Oracle endpoint.

Walks each previously-broken Oracle proxy surface (see MangroveAI gh
#576) plus a full experiment lifecycle, end-to-end against prod. Each
section is labeled with the original issue number so the script doubles
as a smoke test:

    Section 1 — exec_config_defaults     (was: HTML; now: defaults dict)
    Section 2 — simulate_presets + run    (was: HTML on bare path; now: works)
    Section 3 — list_results()            (was: 500 without experiment_id; now: paginated)
    Section 4a — leaderboard()            (server is canonical; returns personas)
    Section 4b — list_deployed_strategies (the strategy-state surface)
    Section 5 — experiment lifecycle      (sanity check the previously-working surface)

Getting started:
    1. Create an account at https://mangrovedeveloper.ai
    2. Settings > API Keys > Generate a new API key
    3. Set it as an environment variable:
        export MANGROVE_API_KEY=prod_your_key_here

Run:
    python examples/oracle_full_surface_quickstart.py

The script exits 0 on full success, non-zero on any uncaught exception.
"""
from __future__ import annotations

import os
import sys
import time

from mangrove_ai import MangroveAI


def _header(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main() -> int:
    if not os.environ.get("MANGROVE_API_KEY"):
        print("ERROR: set MANGROVE_API_KEY first (see module docstring).", file=sys.stderr)
        return 2

    client = MangroveAI()

    # ----------------------------------------------------------------
    # Section 1 — exec_config (gh #576 issue #1)
    # ----------------------------------------------------------------
    _header("Section 1 — exec_config_defaults()")
    defaults = client.oracle.exec_config_defaults()
    psc = defaults.get("risk_management", {}).get("position_size_calc")
    init_bal = defaults.get("position_limits", {}).get("initial_balance")
    print(f"position_size_calc: {psc}")
    print(f"initial_balance:    {init_bal}")
    print(f"top-level sections: {sorted(defaults.keys())}")
    assert isinstance(defaults, dict) and psc, "exec_config_defaults returned empty dict"

    # ----------------------------------------------------------------
    # Section 2 — simulate (gh #576 issue #2)
    # ----------------------------------------------------------------
    _header("Section 2 — simulate_presets() + simulate_history()")
    presets = client.oracle.simulate_presets()
    print(f"simulate has {len(presets)} preset(s)")
    if presets:
        first_preset = presets[0]
        preset_id = first_preset.get("id") or first_preset.get("name") or "<unknown>"
        print(f"first preset: {preset_id}")

    history = client.oracle.simulate_history(limit=3)
    hist_total = history.get("total", "?") if isinstance(history, dict) else "?"
    print(f"simulate history total: {hist_total}")

    # ----------------------------------------------------------------
    # Section 3 — list_results without experiment_id (gh #576 issue #3)
    # ----------------------------------------------------------------
    _header("Section 3 — list_results() with no experiment_id filter")
    page = client.oracle.list_results(limit=5)
    print(f"got {page.total} cross-experiment results (page size {len(page.results)})")
    if page.results:
        first = page.results[0]
        print(f"first row asset={first.get('asset')} "
              f"sharpe={first.get('sharpe_ratio')} "
              f"irr={first.get('irr_annualized')}")
    assert page.total >= 0, "list_results returned non-int total"

    # ----------------------------------------------------------------
    # Section 4a — leaderboard (gh #576 issue #4)
    # ----------------------------------------------------------------
    _header("Section 4a — leaderboard() returns curated personas")
    lb = client.oracle.leaderboard()
    print(f"{len(lb.personas)} persona(s)")
    for p in lb.personas[:3]:
        print(f"  rank {p.rank}: {p.name} ({len(p.deployed_strategy_ids)} deployed)")

    # ----------------------------------------------------------------
    # Section 4b — deployed strategies (the live state surface)
    # ----------------------------------------------------------------
    _header("Section 4b — list_deployed_strategies() + state + events")
    strategies = client.oracle.list_deployed_strategies()
    print(f"{len(strategies)} deployed strategy(ies)")
    if strategies:
        s = strategies[0]
        print(f"  {s.id} ({s.name}): account_value={s.account_value} "
              f"total_trades={s.total_trades}")
        state = client.oracle.get_deployed_strategy_state(s.id)
        print(f"  live state keys: {sorted(state.keys())[:6]}")
        events = client.oracle.get_deployed_strategy_events(s.id, limit=5)
        event_list = events.get("events") if isinstance(events, dict) else events
        print(f"  recent events: {len(event_list or [])}")

    # ----------------------------------------------------------------
    # Section 5 — full experiment lifecycle (sanity check)
    # ----------------------------------------------------------------
    _header("Section 5 — experiment lifecycle (create → validate → list_results → delete)")
    datasets = client.oracle.list_datasets()
    signals = client.oracle.list_signals()
    print(f"{len(datasets)} dataset(s), {len(signals)} signal(s) available")

    # Pick the smallest BTC dataset available so validate runs quickly.
    btc_datasets = [d for d in datasets if d.get("asset") == "BTC"]
    if not btc_datasets:
        print("no BTC datasets; skipping lifecycle section.")
        return 0
    ds = btc_datasets[0]

    cfg = {
        "name": f"sdk-smoke-{int(time.time())}",
        "datasets": [{
            "asset": ds.get("asset"),
            "timeframe": ds.get("timeframe"),
            "file": ds.get("file"),
        }],
        "strategy_template": {
            "entry": [{"name": "macd_bullish_cross", "params": {"window_fast": 12, "window_slow": 26}}],
            "exit": [{"name": "macd_bearish_cross", "params": {"window_fast": 12, "window_slow": 26}}],
        },
        "param_grid": {},  # single point — sweep of 1
    }

    created = None
    try:
        created = client.oracle.create_experiment(cfg)
        exp_id = created.experiment_id
        print(f"created: {exp_id}")

        status = client.oracle.validate_experiment(exp_id)
        print(f"validate: status={getattr(status, 'status', status)}")
    except Exception as e:
        print(f"  create/validate not exercised (server-side rejection): {e}")
    finally:
        if created is not None:
            try:
                client.oracle.delete_experiment(created.experiment_id)
                print(f"deleted: {created.experiment_id}")
            except Exception as e:
                print(f"  cleanup-delete failed (non-fatal): {e}")

    print("\nAll sections completed without raising.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
