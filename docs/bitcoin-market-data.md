# Bitcoin order books, trade flow, and liquidation levels

These additions are prepared for Python 2.8.0 and TypeScript 1.5.0. They depend on the matching [MangroveAI operations](https://github.com/MangroveTechnologies/MangroveAI/pull/1660)
and [MangroveRoots provider implementation](https://github.com/MangroveTechnologies/MangroveRoots/pull/105).
They are not a statement that a
published SDK or deployed API already serves them. Provider configuration and
account entitlements still apply.

The Python methods below each request one bounded REST read. The examples disable
HTTP retries with `auto_retry=False`; the normal client retry policy otherwise
applies. TypeScript uses
the same endpoints through its generated `request` surface. Neither client starts
a stream, collects a history, adds a provider, or automatically follows pages.

| Read | Python method on `client.market_data` | REST path after `/api/v1` | Upstream |
|---|---|---|---|
| Order-book snapshot and best quote | `get_orderbook` | `/market-data/orderbook` | CoinAPI |
| Bounded order-book snapshots over time | `get_orderbook_history` | `/market-data/orderbook/history` | CoinAPI |
| Trades and aggressive buy/sell imbalance | `get_order_flow` | `/market-data/order-flow` | CoinAPI |
| Reported open-position liquidation prices | `get_liquidation_levels` | `/market-data/liquidation-levels` | Nansen, Hyperliquid only |

## Order books and trade flow

Pass an exact spot instrument such as `COINBASE_SPOT_BTC_USD`, rather than an ambiguous
`BTC`. Quote values are in the instrument's quote currency: a BTC/USDT read does
not become USD because the client displays a dollar sign. Trade sizes and book
quantities are in the base currency.

```python
from mangrove_ai import MangroveAI

with MangroveAI(api_key=api_key, auto_retry=False) as client:
    book = client.market_data.get_orderbook(
        "COINBASE_SPOT_BTC_USD", limit_levels=50,
    )
    history = client.market_data.get_orderbook_history(
        "COINBASE_SPOT_BTC_USD",
        "2026-11-19T20:00:00-06:00", "2026-11-19T20:01:00-06:00",
        limit=100, limit_levels=50,
    )
    flow = client.market_data.get_order_flow(
        "COINBASE_SPOT_BTC_USD",
        "2026-11-19T20:00:00-06:00", "2026-11-19T20:01:00-06:00",
        limit=100,
    )
```

The history and flow time ranges must include a timezone and span at most 24
hours. The server accepts at most 1,000 returned items. Current books allow up to
200 levels per side; historical books allow up to 50. Upstream coverage and
entitlements can restrict the response further.

Preserve `coverage`, `limit_reached`, `quality`, and both provider and exchange timestamps
when displaying these results. Quality metadata reports skipped malformed records
and duplicate trades. A response below the requested limit does not
prove that the provider captured every update. Compare the same venue,
instrument, and fixed price bands when assessing bid buildup. A sequence of
snapshots does not separately identify gross new orders and cancellations.

Trade-flow delta and cumulative volume delta describe the returned trades only.
They measure aggressive buying versus selling, not money entering or leaving
Bitcoin. Unknown trade sides must remain outside the buy/sell classification.
Trades alone cannot establish resting bids or reconstruct an order book.

## Liquidation levels

```python
with MangroveAI(api_key=api_key, auto_retry=False) as client:
    levels = client.market_data.get_liquidation_levels(
        "BTC", page=1, per_page=100,
    )
```

This reads one Nansen page of Hyperliquid open positions. The response labels
`venue="hyperliquid"`, `kind="reported_position_liquidation_prices"`, and
`coverage="provider_page"`. A missing liquidation price stays null.
`quality.skipped_records` reports malformed provider rows that were excluded. Keep the
provider's pagination metadata when reporting coverage; fetch another page only
as another explicit request.

A position's reported liquidation price can change as margin, position size, or
market conditions change. These levels are neither realized liquidation events
nor a heatmap estimating positions across centralized exchanges. Do not combine
an incomplete page into a claim about total market exposure.

## TypeScript

```typescript
import { MangroveAI } from '@mangrove-ai/sdk';

const client = new MangroveAI({ apiKey });
const book = await client.request('GET /api/v1/market-data/orderbook', {
  query: { symbol_id: 'COINBASE_SPOT_BTC_USD', limit_levels: 50 },
});
const levels = await client.request('GET /api/v1/market-data/liquidation-levels', {
  query: { token_symbol: 'BTC', page: 1, per_page: 100 },
});
```

The server validates requests and calculates results. The clients preserve its
source, nulls, coverage, and errors. Neither client silently switches providers,
buys an entitlement, or pays an x402 challenge automatically.
