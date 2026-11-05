import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { MangroveAI, APIError, ConfigurationError, RequestAbortedError } from '../dist/index.js';

const fixture = JSON.parse(readFileSync(new URL('../../../contracts/mangroveai/fixtures/local-deployment-not-ready.json', import.meta.url)));
const strategyId = fixture.strategy_id;

test('local deployment preserves the full server snapshot/readiness and sends one authenticated read', async () => {
  let calls = 0;
  const client = new MangroveAI({ apiKey: 'prod_local_fixture', fetch: async (url, options) => {
    calls++;
    assert.equal(String(url), `https://api.mangrovedeveloper.ai/api/v1/strategies/${strategyId}/local-deployment?asset_class=crypto`);
    assert.equal(options.method, 'GET');
    assert.equal(new Headers(options.headers).get('authorization'), 'Bearer prod_local_fixture');
    assert.equal(options.body, undefined);
    return new Response(JSON.stringify(fixture), { headers: { 'content-type': 'application/json' } });
  } });
  assert.deepEqual(await client.strategies.localDeployment(strategyId, { assetClass: 'crypto', timeoutMs: 1000 }), fixture);
  assert.equal(calls, 1);
});
test('ready local snapshots retain a null blocker without activating a runner', async () => {
  let calls = 0;
  const ready = { ...fixture, activation_ready: true, activation_blocker: null };
  const client = new MangroveAI({ apiKey: 'prod_local_fixture', fetch: async () => {
    calls++;
    return new Response(JSON.stringify(ready), { headers: { 'content-type': 'application/json' } });
  } });
  assert.deepEqual(await client.strategies.localDeployment(strategyId, { assetClass: 'crypto' }), ready);
  assert.equal(calls, 1);
});
for (const status of [401, 402, 403, 404, 409, 503]) {
  test(`local deployment retains HTTP${status} diagnostics without payment, activation or retry`, async () => {
    let calls = 0;
    const client = new MangroveAI({ apiKey: 'prod_local_fixture', fetch: async () => {
      calls++;
      return new Response(JSON.stringify({ error: 'DEPLOYMENT_CONFLICT', message: 'Server decision', details: { phase: 'validation' } }),
        { status, headers: { 'x-correlation-id': 'fixture-correlation' } });
    } });
    await assert.rejects(client.strategies.localDeployment(strategyId, { assetClass: 'equity' }), error => {
      assert.ok(error instanceof APIError);
      assert.equal(error.status, status);
      assert.equal(error.correlationId, 'fixture-correlation');
      assert.equal(error.response.details.phase, 'validation');
      return true;
    });
    assert.equal(calls, 1);
  });
}
test('local deployment bad input and an already aborted request stop before transport', async () => {
  let calls = 0;
  const client = new MangroveAI({ apiKey: 'prod_local_fixture', fetch: async () => { calls++; throw new Error('Forbidden'); } });
  for (const [id, options] of [['../not-a-uuid', { assetClass: 'crypto' }], [strategyId, { assetClass: 'options' }], [strategyId, undefined]]) {
    await assert.rejects(client.strategies.localDeployment(id, options), ConfigurationError);
  }
  await assert.rejects(client.strategies.localDeployment(strategyId, { assetClass: 'crypto', signal: AbortSignal.abort() }), RequestAbortedError);
  assert.equal(calls, 0);
});
