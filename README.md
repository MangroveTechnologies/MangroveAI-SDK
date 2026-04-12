# MangroveAI Python SDK

Python SDK for the [MangroveAI](https://mangrovedeveloper.ai) trading strategy platform.

## Install

```bash
pip install mangroveai
```

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
from mangroveai import MangroveAI

client = MangroveAI()  # reads MANGROVE_API_KEY from environment

# List trading signals
signals = client.signals.list(limit=10)
for s in signals.items:
    print(f"{s.name} ({s.category}, {s.signal_type})")

# Get market data
btc = client.crypto_assets.get_market_data("BTC")
print(f"BTC: ${btc.data['current_price']:,.2f}")

# Create a strategy
from mangroveai.models import CreateStrategyRequest

strategy = client.strategies.create(CreateStrategyRequest(
    name="RSI Momentum",
    asset="BTC",
    entry=[{"name": "rsi_oversold", "signal_type": "TRIGGER",
            "timeframe": "1d", "params": {"window": 14, "threshold": 30}}],
))

# Run a backtest
import json
from mangroveai.models import BacktestRequest

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
| `client.signals` | `signals.*` | 7 | Signal discovery, evaluation, validation |
| `client.crypto_assets` | `crypto_assets.*` | 8 | Assets, exchanges, OHLCV, market data |
| `client.execution` | `execution.*` | 8 | Accounts, positions, trades, evaluation |
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

### Layer 3: Coming Soon

On-chain analytics (`client.on_chain`), DeFi data (`client.defi`), and social signals (`client.social`) are defined but not yet available. Calling these methods raises `NotImplementedLayerError`.

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
from mangroveai import MangroveAI, NotFoundError, RateLimitError, APIError

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
git clone https://github.com/MangroveTechnologies/MangroveAI-SDK.git
cd MangroveAI-SDK
pip install -e ".[dev]"
pytest tests/ --ignore=tests/integration  # unit tests
MANGROVE_API_KEY=... pytest tests/integration/ -m integration  # live tests
```
