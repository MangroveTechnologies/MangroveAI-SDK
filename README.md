# MangroveAI Python SDK

[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white&style=for-the-badge)](https://discord.gg/xUcn4R6zJR)

Python SDK for the [MangroveAI](https://mangrovedeveloper.ai) trading strategy platform.

## Install

```bash
pip install mangrove-ai
```

> **Migrating from `mangroveai` (the pre-1.0 package name)?** Two changes:
>
> ```diff
> - pip install mangroveai
> + pip install mangrove-ai
> ```
> ```diff
> - from mangroveai import MangroveAI
> + from mangrove_ai import MangroveAI
> ```
>
> Everything else (the `MangroveAI` client class, every method name, every
> model name) is unchanged. The old `mangroveai` PyPI package will receive
> a final 0.3.2 release with a `DeprecationWarning` and then stop receiving
> updates. See `CHANGELOG.md` `[1.0.0]` for the full rationale.

## Setup

1. Create an account at [mangrovedeveloper.ai](https://mangrovedeveloper.ai)
2. Navigate to **Settings > API Keys**
3. Generate a new API key
4. Set it as an environment variable:

```bash
export MANGROVE_API_KEY=prod_your_key_here
```

## Quickstart

```python
from mangrove_ai import MangroveAI

client = MangroveAI()  # reads MANGROVE_API_KEY from environment

# List trading signals
signals = client.signals.list(limit=10)
for s in signals.items:
    print(f"{s.name} ({s.category}, {s.signal_type})")

# Get market data
btc = client.crypto_assets.get_market_data("BTC")
print(f"BTC: ${btc.data['current_price']:,.2f}")

# Create a strategy
from mangrove_ai.models import CreateStrategyRequest

strategy = client.strategies.create(CreateStrategyRequest(
    name="RSI Momentum",
    asset="BTC",
    entry=[{"name": "rsi_oversold", "signal_type": "TRIGGER",
            "timeframe": "1d", "params": {"window": 14, "threshold": 30}}],
))

# Run a backtest
import json
from mangrove_ai.models import BacktestRequest

result = client.backtesting.run(BacktestRequest(
    asset="BTC",
    interval="1d",
    strategy_json=json.dumps({"name": "test", "asset": "BTC",
        "entry": [{"name": "rsi_oversold", "signal_type": "TRIGGER",
                    "timeframe": "1d", "params": {"window": 14, "threshold": 30}}],
        "exit": []}),
    lookback_months=3,
    initial_balance=10000,
    min_balance_threshold=0.1, min_trade_amount=25,
    max_open_positions=3, max_trades_per_day=10,
    max_risk_per_trade=0.02, max_units_per_trade=1000000,
    max_trade_amount=10000000, volatility_window=24,
    target_volatility=0.1,
    # Optional: per-timeframe cooldown configuration (preferred over legacy flat fields).
    # Keys are the primary timeframe; each value carries max_hold_time_hours,
    # short_loss_limit, long_loss_limit, short_window_bars, and long_window_bars.
    cooldown_config={
        "1d": {
            "max_hold_time_hours": 10,
            "short_loss_limit": 4,
            "long_loss_limit": 6,
            "short_window_bars": 20,
            "long_window_bars": 60,
        }
    },
))
print(f"Trades: {result.trade_count}, Sharpe: {result.metrics.get('sharpe_ratio')}")
```

## Services

### Layer 1: MangroveAI Core API

| Service | Access | Methods | Description |
|---------|--------|---------|-------------|
| `client.auth` | `auth.*` | 5 | Login, refresh, API key management |
| `client.strategies` | `strategies.*` | 8 | Strategy CRUD, status, execution state |
| `client.backtesting` | `backtesting.*` | 7 | Sync/async/bulk backtesting |
| `client.oracle` | `oracle.*` | 28 | SIEVE scoring, parameter sweeps/experiments, corpus data queries, backtests, simulation, leaderboard |
| `client.signals` | `signals.*` | 7 | Signal discovery, evaluation, validation |
| `client.crypto_assets` | `crypto_assets.*` | 8 | Assets, exchanges, OHLCV, market data |
| `client.execution` | `execution.*` | 8 | Accounts, positions, trades, evaluation |
| `client.on_chain` | `on_chain.*` | 11 | Smart-money flows, DEX/perp trades, token holders, whale activity (Nansen + WhaleAlert) |
| `client.defi` | `defi.*` | 3 | Protocol/chain TVL, stablecoin metrics (DeFiLlama) |
| `client.social` | `social.*` | 3 | Topic sentiment, mentions, user influence (X / Twitter) |
| `client.docs` | `docs.*` | 2 | Documentation listing and content |

### Layer 2: Knowledge Base API

| Service | Access | Methods | Description |
|---------|--------|---------|-------------|
| `client.kb.documents` | `kb.documents.*` | 3 | Document listing, content, sections |
| `client.kb.search` | `kb.search.*` | 1 | Full-text search with BM25 ranking |
| `client.kb.tags` | `kb.tags.*` | 2 | Tag listing and filtering |
| `client.kb.glossary` | `kb.glossary.*` | 3 | Glossary terms and backlinks |
| `client.kb.signals` | `kb.signals.*` | 2 | Signal metadata from KB |
| `client.kb.indicators` | `kb.indicators.*` | 2 | Indicator metadata from KB |
| `client.kb.compute` | `kb.compute.*` | 2 | x402 paid signal/indicator computation |

### On-chain capability surface

`client.on_chain` covers Mangrove's Nansen Pro plan plus WhaleAlert (Developer tier, 30-day history):

| Method | Source | What it returns |
|---|---|---|
| `get_onchain_series(symbol, metrics, date_from, date_to, interval, provider)` | Nansen (WhaleAlert fallback) | **Per-bar metric time series** (SmartMoneyNetflow, SmartMoneyHoldings, ExchangeNetflow, WhaleNetInflow, HolderConcentration) — one column per metric |
| `get_smart_money_sentiment(symbol)` | Nansen | Single-token accumulation/distribution score |
| `screen_smart_money(chains, timeframe)` | Nansen | Tokens with high smart-money activity |
| `get_smart_money_historical_holdings(chains, date_range, filters, order_by)` | Nansen | Date-stamped holdings snapshots |
| `get_smart_money_dex_trades(chains, filters, order_by)` | Nansen | Live DEX trades by smart-money wallets |
| `get_smart_money_perp_trades(filters, order_by)` | Nansen (Hyperliquid) | Perpetual-futures trades by smart-money wallets |
| `get_token_holders(symbol)` | Nansen | Holder distribution + concentration |
| `get_token_dex_trades(symbol, chain, date_range, filters, order_by)` | Nansen | Single-token DEX trades across all participants |
| `get_token_flows(symbol, chain, date_range, label, filters, order_by)` | Nansen | Per-wallet-category hourly flow rows (`label` scopes to smart_money/exchange/whale/…; excludes stablecoins) |
| `get_whale_transactions(symbol, min_value, hours_back)` | WhaleAlert | Recent large-value on-chain transactions |
| `get_exchange_flows(symbol, hours_back)` | WhaleAlert | Aggregated exchange inflows/outflows |
| `get_whale_activity(symbol, hours_back)` | WhaleAlert | High-level whale activity summary |

**On-chain time series → signals.** `get_onchain_series` returns a per-bar series for any window — the
same call serves a live trailing window (e.g. last 10 days, ending now) or a long historical range.
Build a DataFrame with `pd.DataFrame(resp.series).set_index("timestamp")` and feed it to a
[`mangrove-kb`](https://pypi.org/project/mangrove-kb/) on-chain signal. End-to-end walkthrough:
`examples/onchain_signals_demo.py`.

`filters` and `order_by` pass through directly to the upstream Nansen API — restrict by
`include_smart_money_labels`, set `value_usd` min/max bounds, sort by any field. See
`examples/on_chain_nansen.py` for raw-method snippets.

## Oracle — SIEVE + sweep

`client.oracle.*` is Mangrove's strategy-research engine. Two headline tools:

- **SIEVE** scores up to 99 strategy ideas in one call and tells you which are worth
  testing — a binary go/no-go (`p_trades` vs `p_no_trades`) plus a 4-class outcome head
  (`losing` / `no_trades` / `wash` / `winning`). Most ideas never trade meaningfully;
  SIEVE finds the ones that do *before* you spend compute backtesting them.
- **Sweep** fans a parameter search into one managed experiment of many backtests and
  ranks the results.

### Score ideas with SIEVE

```python
from mangrove_ai import MangroveAI
from mangrove_ai.models.oracle import SieveScoreRequest, StrategyInput, SignalSpec

client = MangroveAI()  # reads MANGROVE_API_KEY

resp = client.oracle.sieve_score(SieveScoreRequest(strategies=[
    StrategyInput(
        asset="BTC",
        entry=[SignalSpec(name="ema_crossover", signal_type="TRIGGER", timeframe="1h")],
        exit=[SignalSpec(name="rsi", signal_type="FILTER", timeframe="1h")],
    ),
    # ...up to 99 strategies per request
]))

print(f"scored {resp.count} | model {resp.model_version}")
for p in resp.predictions:
    print(f"  go/no-go: {p.binary}")      # {'p_no_trades': .., 'p_trades': ..}
    print(f"  outcome:  {p.four_class}")  # {'losing':.., 'no_trades':.., 'wash':.., 'winning':..}
```

### Run a parameter sweep (experiment lifecycle)

A sweep is a draft experiment you **validate**, then **launch**; it fans out into backtests
asynchronously. Poll `get_experiment` / `list_results` to track it.

```python
# Pick a dataset + execution defaults from the API, then build a config
ds = client.oracle.list_datasets()[0]
exec_config = client.oracle.exec_config_defaults()

config = {
    "name": "ema-sweep-demo",
    "kind": "single",
    "search_mode": "random",
    "seed": 42,
    "n_random": 50,                 # number of random strategies to draw
    "datasets": [ds],
    "random_signals": {
        "n_entry_triggers": 1, "min_entry_filters": 0, "max_entry_filters": 2,
        "min_exit_triggers": 0, "max_exit_triggers": 1,
        "min_exit_filters": 0, "max_exit_filters": 1,
        "n_param_draws": 3, "allowed_categories": None,
    },
    "execution_config": exec_config,
}

created = client.oracle.create_experiment(config)            # -> status "draft"
val = client.oracle.validate_experiment(created.experiment_id)
print(f"valid={val.valid} total_runs={val.total_runs} errors={val.errors}")

if val.valid:                                                # must pass before launch
    client.oracle.launch_experiment(created.experiment_id)   # fans out asynchronously
    status = client.oracle.get_experiment(created.experiment_id)
    print(f"status={status['status']} completed={status.get('completed_runs')}")
    # client.oracle.pause_experiment(id) / delete_experiment(id) to stop or clean up

results = client.oracle.list_results(experiment_id=created.experiment_id, limit=20)
```

### Other `client.oracle.*` methods

- **Backtests:** `backtest`, `backtest_async` + `backtest_poll`, `backtest_bulk`
- **Corpus query:** `data_query` (curated BigQuery proxy over results / ohlcv)
- **Simulation:** `simulate_run`, `simulate_generate`, `simulate_presets`, `simulate_history`
- **Results & catalogs:** `list_results`, `list_datasets`, `list_signals`, `list_templates`, `exec_config_defaults`
- **Leaderboard & live:** `leaderboard`, `list_deployed_strategies`, `get_deployed_strategy_state`, `get_deployed_strategy_events`

Full reference: [SIEVE pre-filter guide](https://docs.mangrovedeveloper.ai/guides/using-sieve-prefilter),
[SIEVE end-to-end](https://docs.mangrovedeveloper.ai/guides/sieve-end-to-end-workflow), and the
[Experiments API reference](https://docs.mangrovedeveloper.ai/api-reference/experiments).

## Environment Detection

The SDK auto-detects the environment from your API key prefix:

| Prefix | Environment | API Base URL |
|--------|-------------|-------------|
| `prod_` | Production | `https://api.mangrovedeveloper.ai/api/v1` |
| `dev_` | Development | `https://devapi.mangrove.trade/api/v1` |

Override with explicit parameters:

```python
client = MangroveAI(api_key="...", base_url="http://localhost:5001/api/v1")
```

## Error Handling

```python
from mangrove_ai import MangroveAI, NotFoundError, RateLimitError, APIError

client = MangroveAI()

try:
    strategy = client.strategies.get("nonexistent-id")
except NotFoundError as e:
    print(f"Not found: {e.message} (correlation_id={e.correlation_id})")
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after}s")
except APIError as e:
    print(f"[{e.status_code}] {e.code}: {e.message}")
```

## Pagination

Paginated endpoints return `PaginatedResponse[T]`:

```python
# Single page
page = client.strategies.list(skip=0, limit=10)
print(f"Showing {len(page.items)} of {page.total}")

# Auto-paginate all items
for strategy in client.strategies.list_iter():
    print(strategy.name)
```

## Examples

See the [`examples/`](examples/) directory for working scripts.

## Development

```bash
git clone https://github.com/MangroveTechnologies/mangrove-ai-sdk.git
cd mangrove-ai-sdk
pip install -e ".[dev]"
pytest tests/ --ignore=tests/integration  # unit tests
MANGROVE_API_KEY=... pytest tests/integration/ -m integration  # live tests
```
