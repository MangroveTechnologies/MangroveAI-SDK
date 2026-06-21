"""MangroveAI SDK -- DeFi Pro Quickstart (DeFiLlama-backed routes)

``client.defi`` exposes DeFiLlama analytics. The TVL / chain / stablecoin
methods are available on any plan. The **Pro** methods below -- token unlocks,
perp funding, treasuries, ETF flows, and lending rates -- require a **Pro,
Startup, or Enterprise** plan; on an unentitled plan they raise
``AuthorizationError`` (HTTP 403, ``TIER_UPGRADE_REQUIRED``) with an upgrade
message. (Agents paying per-call via x402 are not subscription-gated.)

Each paid account also gets **1,000 DeFiLlama Pro calls per month**; beyond
that the methods raise ``RateLimitError`` (HTTP 429, ``quota_exceeded``) until
the monthly period rolls over.

Getting started:
    1. Create an account at https://mangrovedeveloper.ai
    2. Settings -> API Keys -> generate a new key (on a Pro/Startup/Enterprise plan)
    3. ``export MANGROVE_API_KEY=prod_your_key_here``
    4. ``python examples/defi_pro.py``

This doubles as a coverage smoke-test for the DeFi Pro surface -- each section
runs one method and prints a short summary. All calls are billable and count
against the 1,000/month cap.
"""
from __future__ import annotations

from mangrove_ai import MangroveAI
from mangrove_ai.exceptions import AuthorizationError, RateLimitError


def main() -> None:
    client = MangroveAI()  # reads MANGROVE_API_KEY from the environment

    try:
        unlocks = client.defi.get_token_unlocks()
        print(f"[token unlocks]  {unlocks.count} tokens tracked")
        if unlocks.data:
            top = unlocks.data[0]
            print(f"  e.g. {top.get('name')}: circSupply={top.get('circSupply')}")

        funding = client.defi.get_perp_funding()
        print(f"[perp funding]   {funding.count} pools")

        treasuries = client.defi.get_treasuries()
        print(f"[treasuries]     {treasuries.count} protocol treasuries")

        flows = client.defi.get_etf_flows()
        print(f"[etf flows]      {flows.count} flow records")

        lending = client.defi.get_lending_borrow_rates()
        print(f"[lending rates]  {lending.count} lending pools")

    except AuthorizationError as e:
        print(f"DeFi Pro requires a Pro/Startup/Enterprise plan: {e}")
    except RateLimitError as e:
        # 1,000 Pro calls/account/month exhausted -- resets next monthly period.
        print(f"DeFi Pro monthly cap reached (1,000/account/month): {e}")


if __name__ == "__main__":
    main()
