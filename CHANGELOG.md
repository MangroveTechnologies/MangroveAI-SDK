# Changelog

All notable changes to the MangroveAI Python SDK will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
