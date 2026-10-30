import { MangroveAI, type CoreModels, type UsageMetrics } from '../src/index.js';

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
