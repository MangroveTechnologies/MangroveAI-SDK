import { MangroveAI, oracleEffectiveFilters, type CoreModels, type Operations, type OracleEffectiveFilters, type UsageMetrics, type ExecutionConfiguration, type LocalDeployment } from '../src/index.js';

const sdk = new MangroveAI({ apiKey: 'prod_fixture', baseUrl: 'https://example.invalid' });
void sdk.request('GET /api/v1/market-data/orderbook', {
  query: { symbol_id: 'COINBASE_SPOT_BTC_USD', limit_levels: 20, provider: 'coinapi' },
}).then(book => {
  const ask: number | null = book.best_ask;
  const exchangeTime: string | null = book.time_exchange;
  void ask; void exchangeTime;
});
void sdk.request('GET /api/v1/market-data/orderbook/history', {
  query: {
    symbol_id: 'COINBASE_SPOT_BTC_USD', time_start: '2026-11-20T02:00:00Z',
    time_end: '2026-11-20T02:01:00Z', limit: 100, limit_levels: 50,
  },
});
void sdk.request('GET /api/v1/market-data/order-flow', {
  query: {
    symbol_id: 'COINBASE_SPOT_BTC_USD', time_start: '2026-11-20T02:00:00Z',
    time_end: '2026-11-20T02:01:00Z', limit: 100,
  },
});
void sdk.request('GET /api/v1/market-data/liquidation-levels', {
  query: { token_symbol: 'BTC', page: 2, per_page: 50, provider: 'nansen' },
}).then(levels => {
  const venue: string = levels.venue;
  const coverage: string = levels.coverage;
  void venue; void coverage;
});
// @ts-expect-error An exact instrument is required; a venue is not inferred.
void sdk.request('GET /api/v1/market-data/orderbook', {});
// @ts-expect-error A bounded history needs its end timestamp.
void sdk.request('GET /api/v1/market-data/order-flow', { query: { symbol_id: 'COINBASE_SPOT_BTC_USD', time_start: '2026-11-20T02:00:00Z' } });
// @ts-expect-error Snapshot limit is numeric.
void sdk.request('GET /api/v1/market-data/orderbook', { query: { symbol_id: 'COINBASE_SPOT_BTC_USD', limit_levels: '50' } });
// Provider is text in the shared schema; the server restricts this operation to Nansen.
// @ts-expect-error Provider identifiers must be text.
void sdk.request('GET /api/v1/market-data/liquidation-levels', { query: { provider: 123 } });
void sdk.signals.list().then(page => {
  const mode: string | undefined = page.items[0]?.evaluation_mode;
  const provider: string | null | undefined = page.items[0]?.data_provider;
  void mode; void provider;
});
const historicalSignal: CoreModels['api1.Signal'] = {
  name: 'fixture', category: 'social', evaluation_mode: 'frame', data_provider: null,
};
const legacySignal: CoreModels['api1.Signal'] = { name: 'fixture', category: 'social' };
void historicalSignal; void legacySignal;
// @ts-expect-error The capability is text rather than an untyped extra property.
const invalidSignalMode: CoreModels['api1.Signal']['evaluation_mode'] = 123;
// @ts-expect-error The optional provider is nullable text, not a number.
const invalidSignalProvider: CoreModels['api1.Signal']['data_provider'] = 123;
void invalidSignalMode; void invalidSignalProvider;
// Types exported by SDK 1.1 remain usable with the refreshed server schema.
const legacyDefi: CoreModels['api1.DefiProResponse'] = { count: 1, data: {}, success: true };
declare const seriesSignal: CoreModels['api1.SignalTriggerResult'];
const legacyMarketData: unknown[] | undefined = seriesSignal.market_data;
void legacyDefi; void legacyMarketData;
const metrics: Promise<UsageMetrics> = sdk.users.getMyMetrics();
void metrics;
void sdk.request('GET /api/v1/strategies/{strategy_id}', { path: { strategy_id: 'fixture' } });
void sdk.strategyWorkflow.getStrategy({ body: { strategy_id: 'fixture' } });
void sdk.strategyWorkflow.getSweepLimits({});
void sdk.request('GET /api/v1/oracle/results', {
  query: { min_days: 90, max_days: 180, min_avg_daily_return: -0.2, max_avg_daily_return: 0, use_irr_duration_default: false, min_simple_annualized_return: -1, max_simple_annualized_return: 0, min_avg_closed_trade_return: -2, max_avg_closed_trade_return: 0, min_closed_trades: 0, sort: 'simple_annualized_return' },
});
void sdk.request('GET /api/v1/oracle/experiments/{experiment_id}/results', {
  path: { experiment_id: 'fixture' },
  query: { min_days: 0, max_days: 90, min_avg_daily_return: 0, use_irr_duration_default: true, min_closed_trades: 0, sort: 'avg_closed_trade_return' },
});
// @ts-expect-error Historical duration is numeric, not a string.
void sdk.request('GET /api/v1/oracle/results', { query: { min_days: '90' } });
void sdk.request('GET /api/v1/oracle/results', { query: { min_irr: 14 } }).then(page => {
  const filters: OracleEffectiveFilters | null = oracleEffectiveFilters(page);
  const appliedDays: number | null | undefined = filters?.min_days;
  const applied: boolean | null | undefined = filters?.irr_duration_default_applied;
  const notice: string | null | undefined = filters?.notice;
  void appliedDays; void applied; void notice;
  // @ts-expect-error The open result envelope does not type effective_filters; use oracleEffectiveFilters.
  const direct: string = page.effective_filters.notice;
  void direct;
});
void sdk.strategyWorkflow.findSweepRuns({ body: { sort_by: 'irr_annualized', min_irr: 14 } }).then(result => {
  const notice: string | null | undefined = oracleEffectiveFilters(result)?.notice;
  void notice;
});

// @ts-expect-error The contract requires the path identity.
void sdk.request('GET /api/v1/strategies/{strategy_id}', {});
// @ts-expect-error Invented routes are not part of the contract.
void sdk.request('GET /made-up', {});
// @ts-expect-error Canonical workflow required fields are preserved.
void sdk.strategyWorkflow.getSweep({ body: {} });
// @ts-expect-error No undocumented JWT constructor is advertised.
void new MangroveAI({ jwt: 'fixture' });
// @ts-expect-error Metrics are typed counts rather than strings.
const invalid: UsageMetrics = { messages_count: '7' };
void invalid;

// Historical backtests preserve the server's null market identities.
const historical: CoreModels['api2.AsyncBacktestStatusResponse'] = {
  base_token: null, quote_token: null, market_data_venue: null,
};
void historical;

const normalized: ExecutionConfiguration = {
  max_risk_per_trade: 0.02,
  cooldown_model: 'trades',
};
void normalized;
// @ts-expect-error Normalized authoring values are numbers; transport compatibility is separate.
const invalidNormalized: ExecutionConfiguration = { max_risk_per_trade: '0.02' };
void invalidNormalized;
// Additional properties retain legacy transport compatibility; no local policy gate.
const legacyCooldown: ExecutionConfiguration = { cooldown_config: { '1D': { short_window_bars: 1 } } };
void legacyCooldown;

const tradeBreaker: ExecutionConfiguration = {
  cooldown_model: 'trades',
  circuit_breaker: { consecutive_loss_limit: 2, resume_size_fraction: 0.5 },
};
const legacyBreaker: ExecutionConfiguration = { cooldown_model: 'bars', circuit_breaker: null };
void tradeBreaker;
void legacyBreaker;
// @ts-expect-error The canonical model is a declared choice, not an arbitrary string.
const invalidModel: ExecutionConfiguration = { cooldown_model: 'invented' };
// @ts-expect-error Normalized breaker counts are numbers, not numeric strings.
const invalidBreakerCount: ExecutionConfiguration = { circuit_breaker: { consecutive_loss_limit: '2' } };
// @ts-expect-error Normalized pause bars are numbers, not numeric strings.
const invalidPauseBars: ExecutionConfiguration = { circuit_breaker: { pause_bars: '36' } };
// @ts-expect-error The finite breaker object has no invented knobs.
const invalidBreakerField: ExecutionConfiguration = { circuit_breaker: { invented_limit: 2 } };
void invalidModel;
void invalidBreakerCount;
void invalidPauseBars;
void invalidBreakerField;
// Explicit bars objects remain accepted by the transport compatibility branch.
const barsTransport: CoreModels['api1.ExecutionConfiguration'] = {
  cooldown_model: 'bars', cooldown_config: { '1h': { short_window_bars: 1 } },
};
void barsTransport;
// Legacy objects remain accepted by the SDK transport contract; no new local gate.
void sdk.request('POST /api/v1/strategy-workflow/save_strategy', {
  body: { strategy_name: 'Fixture', asset: 'ETH', constraints: { max_risk_per_trade: '0.01', unknown_legacy: [1, null] } },
});

// The named local snapshot read uses the canonical server operation contract.
void sdk.strategies.localDeployment('11111111-2222-3333-4444-555555555555', { assetClass: 'crypto' });
// @ts-expect-error asset class is mandatory and server-declared.
void sdk.strategies.localDeployment('11111111-2222-3333-4444-555555555555', {});
// @ts-expect-error unsupported asset classes are not local deployment contracts.
void sdk.strategies.localDeployment('11111111-2222-3333-4444-555555555555', { assetClass: 'options' });

const nullableLocalBlocker: LocalDeployment['activation_blocker'] = null;
void nullableLocalBlocker;
void sdk.strategies.localDeployment('11111111-2222-3333-4444-555555555555', { assetClass: 'equity' }).then(snapshot => {
  const ready: boolean = snapshot.activation_ready;
  const blocker: string | null = snapshot.activation_blocker;
  void ready; void blocker;
});

// Reject widened any/unknown contracts as well as wrong concrete declarations.
// @ts-expect-error readiness is a boolean, not a string.
const invalidLocalReadiness: LocalDeployment['activation_ready'] = 'ready';
// @ts-expect-error blocker is nullable text, not a number.
const invalidLocalBlocker: LocalDeployment['activation_blocker'] = 1;
void invalidLocalReadiness; void invalidLocalBlocker;
declare const typedLocal: LocalDeployment;
const localUserId: string = typedLocal.owner.user_id;
const localOrgId: string = typedLocal.owner.org_id;
const opaqueLocalField: unknown = typedLocal.snapshot['any_server_owned_field'];
// @ts-expect-error snapshot field values remain opaque until narrowed.
const invalidOpaqueLocal: string = typedLocal.snapshot['any_server_owned_field'];
void localUserId; void localOrgId; void opaqueLocalField; void invalidOpaqueLocal;

// Public HelpBot declarations retain their request and response constraints.
const helpRequest: Operations['POST /api/v1/help/ask']['input'] = { body: { message: 'Fixture question' } };
void helpRequest;
// @ts-expect-error The declared HelpBot JSON request requires a message.
const missingHelpMessage: Operations['POST /api/v1/help/ask']['input'] = { body: {} };
void missingHelpMessage;
// @ts-expect-error Confidence is the server's declared enum, not an arbitrary string.
const invalidHelpConfidence: Operations['POST /api/v1/help/ask']['output'] = { confidence: 'invented' };
void invalidHelpConfidence;

// Preserve the exact generic operation key published in TypeScript1.1.0.
declare const canonicalBacktest: Operations['POST /api/v1/backtests'];
const legacyBacktest: Operations['POST /api/v1/backtests/'] = canonicalBacktest;
const canonicalAgain: Operations['POST /api/v1/backtests'] = legacyBacktest;
void canonicalAgain;
void sdk.request('POST /api/v1/backtests/', canonicalBacktest.input);
// @ts-expect-error the compatibility key inherits the canonical required body.
void sdk.request('POST /api/v1/backtests/', {});

// Status keeps server-owned outcomes, including future strings and older omissions.
void sdk.backtesting.getStatus('fixture').then(status => {
  const verdict: string | null | undefined = status.verdict;
  const checks: string[] | null | undefined = status.failed_checks;
  void verdict; void checks;
});
const futureVerdict: CoreModels['api2.AsyncBacktestStatusResponse'] = {
  verdict: 'FUTURE_SERVER_VERDICT', failed_checks: ['future_check'],
};
// @ts-expect-error The canonical verdict is nullable text, not a numeric extra.
const invalidVerdict: CoreModels['api2.AsyncBacktestStatusResponse']['verdict'] = 123;
// @ts-expect-error Check names are strings, not arbitrary values.
const invalidChecks: CoreModels['api2.AsyncBacktestStatusResponse']['failed_checks'] = [123];
void futureVerdict; void invalidVerdict; void invalidChecks;
declare const exitQuote: Operations["POST /api/v1/execution/exit-quote"];
void sdk.request('POST /api/v1/execution/exit-quote', exitQuote.input).then(result => {
  const price: string = result.minimum_exit_price;
  const profitable: boolean = result.profitable;
  return { price, profitable };
});
// @ts-expect-error Exit quotes require decimal strings so the payload preserves venue precision.
void sdk.request('POST /api/v1/execution/exit-quote', { body: { ...exitQuote.input.body, candidate_price: 100100.10 } });
