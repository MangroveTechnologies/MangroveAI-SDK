import { MangroveAI, type CoreModels, type UsageMetrics, type ExecutionConfiguration } from '../src/index.js';

const sdk = new MangroveAI({ apiKey: 'prod_fixture', baseUrl: 'https://example.invalid' });
const metrics: Promise<UsageMetrics> = sdk.users.getMyMetrics();
void metrics;
void sdk.request('GET /api/v1/strategies/{strategy_id}', { path: { strategy_id: 'fixture' } });
void sdk.strategyWorkflow.getStrategy({ body: { strategy_id: 'fixture' } });
void sdk.strategyWorkflow.getSweepLimits({});

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
  cooldown_config: {
    '1D': { short_window_bars: 1, long_window_bars: 4, short_loss_limit: 1, long_loss_limit: 2 },
    cadence_reference: '1h',
  },
};
void normalized;
// @ts-expect-error Normalized authoring values are numbers; transport compatibility is separate.
const invalidNormalized: ExecutionConfiguration = { max_risk_per_trade: '0.02' };
void invalidNormalized;
// @ts-expect-error All four actual engine entry fields are required, including for aliases.
const missingCooldown: ExecutionConfiguration = { cooldown_config: { '1D': { short_window_bars: 1 } } };
void missingCooldown;

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
// Legacy objects remain accepted by the SDK transport contract; no new local gate.
void sdk.request('POST /api/v1/strategy-workflow/save_strategy', {
  body: { strategy_name: 'Fixture', asset: 'ETH', constraints: { max_risk_per_trade: '0.01', unknown_legacy: [1, null] } },
});
