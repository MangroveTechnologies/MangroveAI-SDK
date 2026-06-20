"""Mangrove SIEVE + Oracle data + Oracle backtest quickstart.

Getting started:
1. Create an account at https://mangrovedeveloper.ai
2. Settings > API Keys > Generate a new API key
3. Set it as an environment variable:
   export MANGROVE_API_KEY=prod_your_key_here

Run:
   python examples/oracle_quickstart.py
"""

from mangrove_ai import MangroveAI
from mangrove_ai.models.oracle import (
    DataQueryFilter,
    DataQueryRequest,
    OracleBacktestRequest,
    OrderBy,
    SieveScoreRequest,
    SignalSpec,
    StrategyInput,
)


def main() -> None:
    client = MangroveAI()  # reads MANGROVE_API_KEY from environment

    # 1. SIEVE-score a candidate strategy before paying for a backtest.
    strategy = StrategyInput(
        asset="BTC",
        entry=[
            SignalSpec(
                name="macd_bullish_cross",
                signal_type="TRIGGER",
                timeframe="1h",
                params={"window_fast": 12, "window_slow": 26, "window_sign": 9},
            ),
            SignalSpec(
                name="is_above_sma",
                signal_type="FILTER",
                timeframe="1h",
                params={"window": 50},
            ),
        ],
        exit=[
            SignalSpec(
                name="macd_bearish_cross",
                signal_type="TRIGGER",
                timeframe="1h",
                params={"window_fast": 12, "window_slow": 26, "window_sign": 9},
            )
        ],
    )

    score = client.oracle.sieve_score(SieveScoreRequest(strategies=[strategy]))
    pred = score.predictions[0]
    print("\n=== SIEVE score ===")
    print(f"model_version: {score.model_version}")
    print(f"code_version:  {score.code_version}")
    print(f"binary:        {pred.binary}")
    print(f"four_class:    {pred.four_class}")

    # Only spend backtest compute on strategies SIEVE thinks will win.
    if pred.four_class["winning"] < 0.3:
        print("\nWinning probability too low — skipping backtest.")
        return

    # 2. Mine the corpus for similar high-IRR analogues you can learn from.
    corpus_hits = client.oracle.data_query(
        DataQueryRequest(
            table="results",
            select=["experiment_id", "asset", "irr_annualized", "total_trades"],
            filters=[
                DataQueryFilter(col="asset", op="=", value="BTC"),
                DataQueryFilter(col="irr_annualized", op=">=", value=50),
                DataQueryFilter(col="total_trades", op=">=", value=20),
            ],
            order_by=[OrderBy(col="irr_annualized", dir="desc")],
            limit=5,
        )
    )
    print("\n=== Top 5 BTC analogues with irr_annualized >= 50% ===")
    for row in corpus_hits.rows:
        print(f"  {row['experiment_id'][:32]:32s}  irr={row['irr_annualized']:.1f}%  trades={row['total_trades']}")

    # 3. Backtest the candidate. Most risk-mgmt fields default server-side.
    bt = client.oracle.backtest(
        OracleBacktestRequest(
            asset="BTC",
            interval="1h",
            strategy_json=strategy.model_dump_json(),
            lookback_months=12,
        )
    )
    print("\n=== Backtest ===")
    print(f"success:        {bt.success}")
    print(f"sharpe_ratio:   {bt.metrics.get('sharpe_ratio')}")
    print(f"total_return:   {bt.metrics.get('total_return')}")
    print(f"trade_count:    {bt.trade_count}")


if __name__ == "__main__":
    main()
