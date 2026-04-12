"""MangroveAI SDK Quickstart

Getting started:
1. Create an account at https://mangrovedeveloper.ai
2. Navigate to Settings > API Keys
3. Generate a new API key
4. Set it as an environment variable:
   export MANGROVE_API_KEY=prod_your_key_here

Then run this script:
   python examples/quickstart.py
"""

from mangroveai import MangroveAI
from mangroveai.models import CreateStrategyRequest, BacktestRequest


def main() -> None:
    # Initialize client -- reads MANGROVE_API_KEY from environment
    # Auto-detects prod/dev from key prefix
    client = MangroveAI()

    # ---- Signals ----
    # List available trading signals
    signals = client.signals.list(limit=10)
    print(f"Available signals: {signals.total}")
    for s in signals.items[:5]:
        print(f"  {s.name} ({s.category}, {s.signal_type})")

    # Search for specific signals
    from mangroveai.models import SearchSignalsRequest
    results = client.signals.search(SearchSignalsRequest(query="rsi", search_type="name"))
    print(f"\nRSI signals: {results.total}")
    for s in results.items:
        print(f"  {s.name}")

    # Get signal details
    rsi = client.signals.get("rsi_oversold")
    print(f"\n{rsi.name}: {rsi.metadata.description}")
    print(f"  Params: {rsi.metadata.params}")

    # ---- Market Data ----
    # Current price and market data
    btc = client.crypto_assets.get_market_data("BTC")
    print(f"\nBTC price: ${btc.data['current_price']:,.2f}")
    print(f"  Market cap: ${btc.data['market_cap']:,.0f}")
    print(f"  24h volume: ${btc.data['volume_24h']:,.0f}")

    # Global market overview
    global_data = client.crypto_assets.get_global_market()
    print(f"\nGlobal market cap: ${global_data.data['total_market_cap_usd']:,.0f}")
    print(f"  BTC dominance: {global_data.data['btc_dominance']:.1f}%")

    # ---- Strategies ----
    # Create a strategy
    strategy = client.strategies.create(CreateStrategyRequest(
        name="SDK Quickstart - RSI Momentum",
        asset="BTC",
        strategy_type="momentum",
        description="Buys BTC when RSI crosses below 30 while price is above 50-period SMA",
        entry=[
            {"name": "rsi_oversold", "signal_type": "TRIGGER", "timeframe": "1d", "params": {"window": 14, "threshold": 30}},
            {"name": "is_above_sma", "signal_type": "FILTER", "timeframe": "1d", "params": {"window": 50}},
        ],
        exit=[],
        reward_factor=2.0,
    ))
    print(f"\nCreated strategy: {strategy.name} (id={strategy.id})")

    # ---- Backtesting ----
    # Backtest the strategy
    import json
    result = client.backtesting.run(BacktestRequest(
        asset="BTC",
        interval="1d",
        strategy_json=json.dumps({
            "name": strategy.name,
            "asset": "BTC",
            "entry": [
                {"name": "rsi_oversold", "signal_type": "TRIGGER", "timeframe": "1d", "params": {"window": 14, "threshold": 30}},
                {"name": "is_above_sma", "signal_type": "FILTER", "timeframe": "1d", "params": {"window": 50}},
            ],
            "exit": [],
        }),
        lookback_months=3,
        initial_balance=10000,
        min_balance_threshold=0.1,
        min_trade_amount=25,
        max_open_positions=3,
        max_trades_per_day=10,
        max_risk_per_trade=0.02,
        max_units_per_trade=1000000,
        max_trade_amount=10000000,
        volatility_window=24,
        target_volatility=0.1,
    ))

    if result.success:
        print(f"\nBacktest results ({result.trade_count} trades):")
        for key, value in (result.metrics or {}).items():
            if isinstance(value, float):
                print(f"  {key}: {value:.4f}")
            else:
                print(f"  {key}: {value}")
    else:
        print(f"\nBacktest failed: {result.error}")

    # ---- Cleanup ----
    try:
        client.strategies.delete(strategy.id)
        print(f"\nCleaned up strategy {strategy.id}")
    except Exception as e:
        print(f"\nNote: could not delete strategy (may require strategy:delete permission): {e}")

    client.close()


if __name__ == "__main__":
    main()
