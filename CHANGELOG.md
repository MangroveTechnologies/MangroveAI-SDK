# Changelog

All notable changes to the MangroveAI Python SDK will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
