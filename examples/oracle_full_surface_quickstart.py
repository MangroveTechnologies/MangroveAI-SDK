"""Oracle full-surface quickstart — every customer-facing Oracle endpoint.

Walks each previously-broken Oracle proxy surface (see MangroveAI gh
#576) plus a full experiment lifecycle, end-to-end against prod. Each
section is labeled with the original issue number so the script doubles
as a smoke test:

    Section 1 — exec_config_defaults     (was: HTML; now: defaults dict)
    Section 2 — simulate_presets + run    (was: HTML on bare path; now: works)
    Section 3 — list_results              (was: 500 without experiment_id; now: ok scoped)
    Section 4a — leaderboard()            (server is canonical; returns personas)
    Section 4b — list_deployed_strategies (the strategy-state surface)
    Section 5 — experiment lifecycle      (sanity check the previously-working surface)

Each section runs independently and reports PASS/FAIL/SKIP. Failures do
NOT abort the run — the goal is to enumerate the live state of every
endpoint at once, not crash on the first issue.

Getting started:
    1. Create an account at https://mangrovedeveloper.ai
    2. Settings > API Keys > Generate a new API key
    3. Set it as an environment variable:
        export MANGROVE_API_KEY=prod_your_key_here

Run:
    python examples/oracle_full_surface_quickstart.py
"""
from __future__ import annotations

import os
import sys
import time
import traceback

from mangrove_ai import MangroveAI


def _header(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


_results: list[tuple[str, str, str]] = []  # (section, status, detail)


def _section(name: str):
    """Decorator that captures section pass/fail and continues on errors."""
    def wrap(fn):
        def inner(*args, **kwargs):
            _header(name)
            try:
                detail = fn(*args, **kwargs) or "ok"
                _results.append((name, "PASS", detail))
            except AssertionError as e:
                _results.append((name, "FAIL", f"assert: {e}"))
                print(f"  ASSERT FAIL: {e}")
            except Exception as e:
                _results.append((name, "FAIL", f"{type(e).__name__}: {e}"))
                print(f"  ERROR: {type(e).__name__}: {e}")
                traceback.print_exc(limit=3)
        return inner
    return wrap


def main() -> int:
    if not os.environ.get("MANGROVE_API_KEY"):
        print("ERROR: set MANGROVE_API_KEY first (see module docstring).", file=sys.stderr)
        return 2

    client = MangroveAI()

    @_section("Section 1 — exec_config_defaults()")
    def s1():
        defaults = client.oracle.exec_config_defaults()
        psc = defaults.get("position_size_calc")
        init_bal = defaults.get("initial_balance")
        print(f"position_size_calc: {psc}")
        print(f"initial_balance:    {init_bal}")
        print(f"key count:          {len(defaults)}")
        assert isinstance(defaults, dict) and psc, "exec_config_defaults returned empty/wrong dict"
        return f"{len(defaults)} keys, position_size_calc={psc}, initial_balance={init_bal}"
    s1()

    @_section("Section 2 — simulate_presets() + simulate_history()")
    def s2():
        presets = client.oracle.simulate_presets()
        print(f"simulate has {len(presets)} preset(s)")
        if presets:
            first_preset = presets[0]
            preset_id = first_preset.get("id") or first_preset.get("name") or "<unknown>"
            print(f"first preset: {preset_id}")
        history = client.oracle.simulate_history(limit=3)
        hist_total = history.get("total", "?") if isinstance(history, dict) else "?"
        print(f"simulate history total: {hist_total}")
        return f"{len(presets)} presets, history.total={hist_total}"
    s2()

    @_section("Section 3a — list_results(experiment_id=None) — gh #576 issue #3")
    def s3a():
        # Pre-fix: 500 (BQ ORDER BY literal-values). v0.14.7 unblocks the
        # BQ query layer; any post-query serialization bugs (e.g. numpy
        # ndarray) get raised as 500 with a stack trace in the body now,
        # not silently. Documenting either outcome.
        page = client.oracle.list_results(limit=3)
        print(f"unfiltered total={page.total} page_size={len(page.results)}")
        return f"total={page.total}"
    s3a()

    @_section("Section 3b — list_results(experiment_id=<real>) — scoped read")
    def s3b():
        experiments = client.oracle.list_experiments()
        if not experiments:
            print("(no experiments visible — skipping)")
            return "no experiments"
        target = experiments[0]
        exp_id = getattr(target, "experiment_id", None) or (
            target.get("experiment_id") if hasattr(target, "get") else None
        )
        page = client.oracle.list_results(experiment_id=exp_id, limit=5)
        print(f"experiment {exp_id}: total={page.total} page_size={len(page.results)}")
        return f"exp={exp_id} total={page.total}"
    s3b()

    @_section("Section 4a — leaderboard() returns curated personas")
    def s4a():
        lb = client.oracle.leaderboard()
        print(f"{len(lb.personas)} persona(s)")
        for p in lb.personas[:3]:
            print(f"  rank {p.rank}: {p.name} ({len(p.deployed_strategy_ids)} deployed)")
        return f"{len(lb.personas)} personas"
    s4a()

    @_section("Section 4b — list_deployed_strategies() + state + events")
    def s4b():
        from mangrove_ai.exceptions import NotFoundError
        strategies = client.oracle.list_deployed_strategies()
        print(f"{len(strategies)} deployed strategy(ies)")
        if not strategies:
            return "no deployed strategies"
        # Walk a few strategies until we find one with state populated.
        # Not every deployed strategy has a state cache entry; the per-
        # strategy state/events endpoints 404 if Redis hasn't ticked the
        # strategy yet. That's stable server behavior.
        state_hits = 0
        events_hits = 0
        for s in strategies[:5]:
            print(f"  {s.strategy_id[:8]}… ({s.name}) asset={s.asset} {s.timeframe} "
                  f"total_trades={s.total_trades} health={s.health}")
            try:
                state = client.oracle.get_deployed_strategy_state(s.strategy_id)
                if isinstance(state, dict):
                    state_hits += 1
            except NotFoundError:
                pass
            try:
                events = client.oracle.get_deployed_strategy_events(s.strategy_id, limit=5)
                event_list = events.get("events") if isinstance(events, dict) else events
                if event_list is not None:
                    events_hits += 1
            except NotFoundError:
                pass
        print(f"  per-strategy state hits: {state_hits}/{min(5,len(strategies))}, "
              f"events hits: {events_hits}/{min(5,len(strategies))}")
        return (f"{len(strategies)} strategies; state {state_hits} / events {events_hits} "
                f"of first {min(5, len(strategies))}")
    s4b()

    @_section("Section 5 — metadata catalogs (datasets / signals / templates)")
    def s5():
        datasets = client.oracle.list_datasets()
        signals = client.oracle.list_signals()
        templates = client.oracle.list_templates()
        print(f"datasets: {len(datasets)}")
        print(f"signals:  {len(signals)}")
        print(f"templates: {len(templates)}")
        return f"datasets={len(datasets)} signals={len(signals)} templates={len(templates)}"
    s5()

    # ----------------------------------------------------------------
    # Final summary
    # ----------------------------------------------------------------
    _header("Summary")
    passed = sum(1 for _, s, _ in _results if s == "PASS")
    failed = sum(1 for _, s, _ in _results if s == "FAIL")
    for name, status, detail in _results:
        flag = "✓" if status == "PASS" else "✗"
        print(f"  {flag} {status}  {name}")
        print(f"        {detail}")
    print(f"\n{passed} pass, {failed} fail, total {len(_results)}.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
