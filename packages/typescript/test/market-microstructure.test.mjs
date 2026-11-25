import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { MangroveAI, APIError, ConfigurationError } from '../dist/index.js';

const key = 'prod_fixture_not_a_credential';
const response = (value, status = 200) => new Response(JSON.stringify(value), {
  status, headers: { 'Content-Type': 'application/json' },
});

test('liquidation levels preserve missing prices, venue and incomplete-page coverage', async () => {
  const payload = JSON.parse(await readFile(
    new URL('../../../contracts/mangroveai/fixtures/liquidation-levels-page.json', import.meta.url), 'utf8',
  ));
  let calls = 0;
  const sdk = new MangroveAI({ apiKey: key, fetch: async (url, options) => {
    calls++;
    assert.equal(new URL(url).pathname, '/api/v1/market-data/liquidation-levels');
    assert.equal(options.method, 'GET');
    assert.equal(options.headers.get('Authorization'), `Bearer ${key}`);
    assert.deepEqual(Object.fromEntries(new URL(url).searchParams), {
      token_symbol: 'BTC', page: '1', per_page: '100', provider: 'nansen',
    });
    return response(payload);
  } });
  assert.deepEqual(await sdk.request('GET /api/v1/market-data/liquidation-levels', {
    query: { token_symbol: 'BTC', page: 1, per_page: 100, provider: 'nansen' },
  }), payload);
  assert.equal(calls, 1);
});

for (const path of ['orderbook/history', 'order-flow']) {
  test(`${path} preserves the exact instrument and bounded offset-aware window`, async () => {
    const query = {
      symbol_id: 'COINBASE_SPOT_BTC_USD', time_start: '2026-11-19T20:00:00-06:00',
      time_end: '2026-11-20T02:01:00Z', limit: 17, provider: 'coinapi',
    };
    const payload = { data: [], coverage: 'bounded_provider_response', limit_reached: true };
    let calls = 0;
    const sdk = new MangroveAI({ apiKey: key, fetch: async (url, options) => {
      calls++;
      assert.equal(new URL(url).pathname, `/api/v1/market-data/${path}`);
      assert.equal(options.method, 'GET');
      assert.deepEqual(Object.fromEntries(new URL(url).searchParams), { ...query, limit: '17' });
      return response(payload);
    } });
    assert.deepEqual(await sdk.request(`GET /api/v1/market-data/${path}`, { query }), payload);
    assert.equal(calls, 1);
  });
}

test('book snapshot refuses a missing exact instrument before transport', async () => {
  let calls = 0;
  const sdk = new MangroveAI({ apiKey: key, fetch: async () => {
    calls++;
    return response({});
  } });
  await assert.rejects(sdk.request('GET /api/v1/market-data/orderbook', {}), ConfigurationError);
  assert.equal(calls, 0);
});

test('provider failure is kept without changing provider or following pages', async () => {
  let calls = 0;
  const sdk = new MangroveAI({ apiKey: key, fetch: async () => {
    calls++;
    return response({ error: 'provider_unavailable', code: 'PROVIDER_UNAVAILABLE' }, 503);
  } });
  await assert.rejects(sdk.request('GET /api/v1/market-data/liquidation-levels', {}), error => {
    assert.ok(error instanceof APIError);
    assert.equal(error.status, 503);
    return true;
  });
  assert.equal(calls, 1);
});
