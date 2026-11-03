import { MangroveAI, type CoreModels, type Operations, type UsageMetrics, type ExecutionConfiguration, type LocalDeployment } from '../src/index.js';

const sdk = new MangroveAI({ apiKey: 'prod_fixture', baseUrl: 'https://example.invalid' });
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
