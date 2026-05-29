# Changelog

All notable changes to the MangroveAI Python SDK will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]


### Added -- `client.execution` covers bulk + by-object + portfolio

Three new methods on `ExecutionService` that close the loop on the
`/api/v1/execution/*` surface MangroveAI has exposed since v3.4 but
the SDK never typed:

- `evaluate_by_object(strategy, persist=False)` -- evaluate an inline
  strategy dict WITHOUT persisting it to the DB first. Useful for
  draft testing, dry-runs, and parameter exploration.
- `evaluate_bulk(strategy_ids=[...], strategy_configs=[...], persist=False)`
  -- evaluate N strategies in one HTTP call with shared
  `(asset, timeframe)` market-data fetches. Per-strategy failures
  captured in each result's `error` field without aborting the batch.
  Retires the N+1 fan-out that `live-strategies/run_cron.py` worked
  around with direct httpx calls.
- `get_portfolio(strategy_ids=[...])` -- batched dashboard read:
  name + asset + status + execution_state + open_positions_count +
  last 5 trades for N strategies, in one call. Max 100 IDs per
  request (client-side validation).

New Pydantic response models in `mangrove_ai.models.execution`:
`BulkEvaluateResult`, `PortfolioResponse`, `PortfolioEntry`,
`PortfolioRecentTrade`. `EvaluateResult` gains an optional `error`
field for bulk-mode per-strategy failures.

New customer quickstart: `examples/execution_bulk_quickstart.py`.


### Added -- `client.on_chain` expanded to full Nansen Pro coverage

Five new methods on `client.on_chain`, each POSTing a JSON body that mirrors
the upstream Nansen API shape so customers get the full filter / order_by
capability the Pro plan unlocks:

- `get_smart_money_historical_holdings(chains, date_from, date_to, filters, order_by, page, per_page)`
- `get_smart_money_dex_trades(chains, filters, order_by, page, per_page)`
- `get_smart_money_perp_trades(filters, order_by, page, per_page)` -- Hyperliquid
- `get_token_dex_trades(symbol, chain, date_from, date_to, filters, order_by, page, per_page)`
- `get_token_flows(symbol, chain, date_from, date_to, filters, order_by, page, per_page)`

The on-chain surface now totals **11 methods** (was 6). All Nansen routes
forward `filters` and `order_by` straight through to the upstream API --
e.g. restrict smart-money DEX trades to `Fund`-labelled wallets, sort by
`block_timestamp DESC`, bound `value_usd` min/max.

New Pydantic response models in `mangrove_ai.models.on_chain`:
`SmartMoneyHistoricalHoldingsResponse`, `SmartMoneyDexTradesResponse`,
`SmartMoneyPerpTradesResponse`, `TokenDexTradesResponse`, `TokenFlowsResponse`.

New customer quickstart: `examples/on_chain_nansen.py`.

### Fixed -- README on-chain availability

The README previously said `client.on_chain` was "defined but not yet
available -- raises `NotImplementedLayerError`." That has been incorrect
for months; the service exposes 6 working methods today, and this release
adds 5 more for 11 total.

## [1.0.0] - 2026-05-26

### Renamed (breaking)

- **PyPI distribution: `mangroveai` → `mangrove-ai`.** Install with
  `pip install mangrove-ai`. The old `mangroveai` package will receive a
  final 0.3.2 release containing only a `DeprecationWarning` and then
  stop receiving updates.
- **Python import: `from mangroveai import …` → `from mangrove_ai import …`.**
  (Python module names use underscores; PyPI distribution names use
  hyphens — same as `scikit-learn` → `import sklearn`.)
- **Repository: `MangroveTechnologies/MangroveAI-SDK` → `mangrove-ai-sdk`.**
  GitHub redirects old URLs.

Rationale: the old `mangroveai` package collided constantly with the
`MangroveAI` backend repo when navigating between them. The TypeScript
SDK already publishes as `@mangrove-ai/sdk`; this rename aligns Python
with the established brand convention.

### Migrating

```diff
- pip install mangroveai
+ pip install mangrove-ai
```
```diff
- from mangroveai import MangroveAI
+ from mangrove_ai import MangroveAI
```
The `MangroveAI` client class name is unchanged. Every other public
symbol is unchanged. Only the package and import names differ.

### Added

- `client.oracle` — `OracleService` covering the MangroveOracle endpoints
  reached via MangroveAI's reverse proxy:
  - `sieve_score(request)` — score up to 99 strategies through the
    Mangrove SIEVE classifier (binary + 4-class probabilities, with
    `model_version` + `code_version` provenance). Client-side enforces
    the 99-item cap before the request goes out.
  - `data_query(request)` — query the curated Oracle corpus (results /
    OHLCV) through the BigQuery proxy.
  - `backtest(request)`, `backtest_async(request)`, `backtest_poll(id)`,
    `backtest_bulk(request)` — full backtest surface against Oracle's
    engine.
- New Pydantic models under `mangrove_ai.models.oracle`: `SieveScoreRequest`,
  `SievePrediction`, `SieveScoreResponse`, `StrategyInput`, `RunInput`,
  `SignalSpec`, `DataQueryRequest`, `DataQueryResponse`, `DataQueryFilter`,
  `OracleBacktestRequest`, `OracleBulkBacktestRequest`,
  `OracleBacktestResult`, `OracleAsyncBacktestSubmission`,
  `OracleAsyncBacktestStatus`, `OracleBulkBacktestResult`. All re-exported
  from `mangrove_ai.models`.
- `examples/oracle_quickstart.py` — runnable end-to-end example
  exercising SIEVE → data_query → backtest.

### Production stability

- Project classifier promoted from `Development Status :: 3 - Alpha` to
  `Development Status :: 5 - Production/Stable`. The 1.0 release commits
  to semantic-versioning compatibility going forward.

## [0.3.0] - 2026-04-24

### Added

- `client.config` service with two methods:
  - `trading_defaults()` — full nested `trading_defaults.json` contents from the server.
  - `execution_defaults()` — the flattened execution config the server applies by default.
- Both endpoints are unauthenticated (non-secret public configuration). Backed by
  MangroveAI's new `/api/v1/config/trading-defaults` and `/api/v1/config/execution-defaults`
  routes (MangroveAI #437).

### Changed

- `BacktestRequest` and `BulkBacktestRequest`: trading-config fields that used to be
  required now accept `None` and fall back to the server's `trading_defaults.json`.
  Only `asset` / `interval` / `strategy_json` (and `start_date` / `end_date` on bulk)
  stay required. Explicit values still take precedence.
- Relaxed fields: `initial_balance`, `min_balance_threshold`, `min_trade_amount`,
  `max_open_positions`, `max_trades_per_day`, `max_risk_per_trade`,
  `max_units_per_trade`, `max_trade_amount`, `volatility_window`, `target_volatility`.
- Callers that still pass explicit values work exactly as before — this is a
  relax, not a breaking change.

## [0.2.0] - 2026-04-22

### Added

- `cooldown_config` field on `BacktestRequest` and `BulkBacktestRequest` -- a dict keyed by primary
  timeframe (e.g. `"5m"`, `"15m"`, `"1h"`, `"1d"`) where each value carries `max_hold_time_hours`,
  `short_loss_limit`, `long_loss_limit`, `short_window_bars`, and `long_window_bars`. This is the
  preferred replacement for the old flat cooldown fields.

### Deprecated

- Top-level fields `cooldown_bars`, `daily_momentum_limit`, `weekly_momentum_limit`, and
  `max_hold_time_hours` on `BacktestRequest` and `BulkBacktestRequest`. These fields continue to
  work and are forwarded to the API during the 90-day grace period, but will be removed in a future
  major version. Use `cooldown_config` instead. A `DeprecationWarning` is emitted at model
  construction time when any of these fields are set.

---

## [0.1.0] - 2026-04-12

### Added

**Layer 1 -- MangroveAI Core API (45 methods)**
- `client.auth` -- login, refresh, API key management (5 methods)
- `client.strategies` -- CRUD, status updates, execution state (8 methods)
- `client.backtesting` -- sync, async, bulk backtesting with polling (7 methods)
- `client.signals` -- discovery, search, match, evaluate, validate (7 methods)
- `client.crypto_assets` -- assets, exchanges, OHLCV, market data, trending (8 methods)
- `client.execution` -- accounts, positions, trades, strategy evaluation (8 methods)
- `client.docs` -- documentation listing and content (2 methods)

**Layer 2 -- Knowledge Base API (15 methods)**
- `client.kb.documents` -- document listing, content, sections (3 methods)
- `client.kb.search` -- full-text search with BM25 ranking (1 method)
- `client.kb.tags` -- tag listing and filtering (2 methods)
- `client.kb.glossary` -- glossary terms and backlinks (3 methods)
- `client.kb.signals` -- signal metadata from KB (2 methods)
- `client.kb.indicators` -- indicator metadata from KB (2 methods)
- `client.kb.compute` -- x402 paid signal/indicator computation (2 methods)

**Layer 3 -- Stubs (12 methods)**
- `client.on_chain` -- smart money, whale activity, exchange flows (6 methods, raises NotImplementedLayerError)
- `client.defi` -- protocol TVL, chain TVL, stablecoin metrics (3 methods, raises NotImplementedLayerError)
- `client.social` -- sentiment, mentions, influence scoring (3 methods, raises NotImplementedLayerError)

**Infrastructure**
- Transport layer with httpx, retry logic, and exponential backoff
- Auth strategies: API key, JWT with auto-refresh, x402 wallet, NoAuth
- Environment auto-detection from API key prefix (dev/prod)
- Multi-service routing (MangroveAI API + KB API with separate base URLs)
- PaginatedResponse with auto-pagination iterators
- Custom exception hierarchy matching server error format
- MockTransport for unit testing
- 41 Pydantic v2 response/request models with forward compatibility (extra="allow")
- 72 unit tests, 24 integration tests against live API
- Quickstart example verified against production
