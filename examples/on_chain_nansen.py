"""MangroveAI SDK -- On-Chain Quickstart (Nansen-backed routes)

The ``client.on_chain`` service exposes Mangrove's full Nansen Pro coverage:
smart-money flows, holdings, and DEX/perp trades, plus per-token DEX trades
and wallet-category flows. All filter and sort capabilities of the upstream
Nansen API pass through directly -- you can restrict smart-money trades to
specific wallet labels, set ``value_usd`` min/max bounds, sort by any field,
and so on.

Getting started:
    1. Create an account at https://mangrovedeveloper.ai
    2. Settings -> API Keys -> generate a new key
    3. ``export MANGROVE_API_KEY=prod_your_key_here``
    4. ``python examples/on_chain_nansen.py``

This example also doubles as a coverage smoke-test for the on-chain surface --
each section runs one method and prints a short summary of the response. All
calls are billable; total cost is ~$0.16 at current x402 pricing.
"""

from __future__ import annotations

from datetime import date, timedelta

from mangrove_ai import MangroveAI


def _trailing_window(days: int = 7) -> tuple[str, str]:
    """Return (from, to) ISO date strings for a trailing window ending today."""
    today = date.today()
    return (today - timedelta(days=days)).isoformat(), today.isoformat()


def main() -> None:
    client = MangroveAI()  # Auto-reads MANGROVE_API_KEY from env
    date_from, date_to = _trailing_window(days=7)

    # ------------------------------------------------------------------
    # Smart Money -- broad cross-token reads
    # ------------------------------------------------------------------
    print("=== Smart Money historical holdings (last 7 days, ethereum) ===")
    hh = client.on_chain.get_smart_money_historical_holdings(
        chains=["ethereum"],
        date_from=date_from,
        date_to=date_to,
        per_page=5,
    )
    print(f"  {hh.count} rows over {hh.date_range}")
    for row in (hh.holdings or [])[:3]:
        print(
            f"   - {row.get('date')}  {row.get('token_symbol')}  "
            f"holders={row.get('holders_count')}  value=${row.get('value_usd', 0):,.0f}"
        )

    print("\n=== Smart Money DEX trades (most recent, full passthrough) ===")
    # Use the full Nansen filter / sort vocabulary: restrict to Fund-labelled
    # wallets and sort by most recent trade first.
    trades = client.on_chain.get_smart_money_dex_trades(
        chains=["ethereum"],
        filters={"include_smart_money_labels": ["Fund"]},
        order_by=[{"field": "block_timestamp", "direction": "DESC"}],
        per_page=5,
    )
    print(f"  {trades.count} trades; filter={trades.filters}")
    for t in (trades.trades or [])[:3]:
        print(
            f"   - {t.get('block_timestamp')}  {t.get('trader_address_label')}  "
            f"{t.get('action')}  ${t.get('value_usd', 0):,.0f}"
        )

    print("\n=== Smart Money perp trades on Hyperliquid ===")
    perps = client.on_chain.get_smart_money_perp_trades(per_page=5)
    print(f"  {perps.count} trades on {perps.venue}")
    for t in (perps.trades or [])[:3]:
        print(
            f"   - {t.get('trader_address_label')}  {t.get('side')}  "
            f"{t.get('action')}  {t.get('token_symbol')}  ${t.get('value_usd', 0):,.0f}"
        )

    # ------------------------------------------------------------------
    # Token-scoped -- per-token deep dive
    # ------------------------------------------------------------------
    print("\n=== Token DEX trades -- UNI, last 7 days ===")
    # Pass a CoinGecko ID (preferred) or symbol; we resolve to the on-chain
    # contract address automatically.
    uni_trades = client.on_chain.get_token_dex_trades(
        "uniswap",
        chain="ethereum",
        date_from=date_from,
        date_to=date_to,
        order_by=[{"field": "block_timestamp", "direction": "DESC"}],
        per_page=5,
    )
    print(f"  {uni_trades.count} trades for {uni_trades.symbol} on {uni_trades.chain}")
    print(f"  contract: {uni_trades.contract_address}")
    for t in (uni_trades.trades or [])[:3]:
        print(
            f"   - {t.get('block_timestamp')}  {t.get('action')}  "
            f"{t.get('trader_address_label', 'unlabelled')}"
        )

    print("\n=== Token flows -- UNI, last 7 days (per-wallet-category) ===")
    # The flows endpoint aggregates inflows/outflows by wallet category
    # (smart-money, whales, exchanges, fresh wallets, public figures).
    # Stablecoins are not supported -- the SDK raises NotFoundError if so.
    flows = client.on_chain.get_token_flows(
        "uniswap",
        chain="ethereum",
        date_from=date_from,
        date_to=date_to,
        per_page=5,
    )
    print(f"  {flows.count} hourly snapshots for {flows.symbol}")
    for f in (flows.flows or [])[:3]:
        print(
            f"   - {f.get('date')}  price=${f.get('price_usd', 0):.4f}  "
            f"holders={f.get('holders_count')}  "
            f"in={f.get('total_inflows_count')}/out={f.get('total_outflows_count')}"
        )

    # ------------------------------------------------------------------
    # Pre-existing on-chain routes (also Nansen + WhaleAlert backed)
    # ------------------------------------------------------------------
    print("\n=== Smart Money sentiment (UNI) -- existing route, still works ===")
    sentiment = client.on_chain.get_smart_money_sentiment("UNI")
    print(
        f"  {sentiment.symbol}: {sentiment.sentiment}  "
        f"(net flow {sentiment.net_flow_usd:,.0f} USD over 24h)"
    )

    print("\n=== Whale transactions ($1M+ in last 24h) ===")
    whales = client.on_chain.get_whale_transactions(min_value=1_000_000, hours_back=24)
    print(f"  {whales.count} transactions >= ${whales.min_value_usd:,.0f}")
    for tx in (whales.transactions or [])[:3]:
        print(
            f"   - {tx.get('symbol', '?').upper()}  ${tx.get('amount_usd', 0):,.0f}  "
            f"{tx.get('from_owner', '?')} -> {tx.get('to_owner', '?')}"
        )


if __name__ == "__main__":
    main()
