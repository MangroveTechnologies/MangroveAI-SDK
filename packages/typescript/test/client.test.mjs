import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import test from 'node:test';
import { MangroveAI, APIError, ConfigurationError, MalformedResponseError,
  RequestTimeoutError, RequestAbortedError } from '../dist/index.js';

const fakeKey = 'prod_fixture_key_not_a_credential';
const fixture = async name => JSON.parse(await readFile(new URL(`../../../contracts/mangroveai/fixtures/${name}.json`, import.meta.url), 'utf8'));
const json = (value, status = 200, headers = {}) => new Response(JSON.stringify(value), {
  status, headers: { 'Content-Type': 'application/json', ...headers },
});
const client = (fetch, options = {}) => new MangroveAI({ apiKey: fakeKey, fetch, ...options });

test('usage first call consumes the shared fixture and sends exactly Bearer GET', async () => {
  const value = await fixture('usage-success');
  let calls = 0;
  const sdk = client(async (url, options) => {
    calls++;
    assert.equal(String(url), 'https://api.mangrovedeveloper.ai/api/v1/users/me/metrics');
    assert.equal(options.method, 'GET');
    assert.equal(options.headers.get('Authorization'), `Bearer ${fakeKey}`);
    assert.equal(options.headers.get('X-API-Key'), null);
    assert.equal(options.redirect, 'error');
    assert.equal(options.body, undefined);
    return json(value);
  });
  assert.deepEqual(await sdk.users.getMyMetrics(), value.metrics);
  assert.equal(calls, 1);
});

test('execution metadata uses the shared fixture with no automatic schema gate or extra calls', async () => {
  const value = await fixture('execution-config-success');
  let calls = 0;
  const sdk = client(async (url, options) => {
    calls++;
    assert.equal(String(url), 'https://api.mangrovedeveloper.ai/api/v1/config/execution-config-schema');
    assert.equal(options.method, 'GET');
    assert.equal(options.headers.get('Authorization'), `Bearer ${fakeKey}`);
    return json(value);
  });
  assert.equal(calls, 0);
  const result = await sdk.request('GET /api/v1/config/execution-config-schema', {});
  assert.deepEqual(result.json_schema, value.json_schema);
  assert.deepEqual(result.param_glossary.cooldown_config.required_fields,
    value.json_schema.properties.cooldown_config.additionalProperties.required);
  assert.equal(calls, 1);
});

test('v1 base override routes v2 to the same origin', async () => {
  const requests = [];
  const sdk = client(async url => { requests.push(String(url)); return json(await fixture('backtest-running')); }, { baseUrl: 'https://test-v1.example.invalid/api/v1' });
  await sdk.backtesting.getStatus('00000000-0000-4000-8000-000000000001');
  assert.equal(requests[0], 'https://test-v1.example.invalid/api/v2/backtests/00000000-0000-4000-8000-000000000001/status');
});

test('environment configuration never sends a dev key to production', () => {
  const previous = process.env.MANGROVE_BASE_URL;
  delete process.env.MANGROVE_BASE_URL;
  try {
    assert.throws(() => new MangroveAI({ apiKey: 'dev_fixture' }), ConfigurationError);
    assert.throws(() => new MangroveAI({ apiKey: 'dev_fixture', environment: 'prod' }), ConfigurationError);
    assert.equal(new MangroveAI({ apiKey: 'dev_fixture', baseUrl: 'https://explicit-dev.example.invalid/api/v1' }).baseUrl, 'https://explicit-dev.example.invalid');
  } finally {
    if (previous === undefined) delete process.env.MANGROVE_BASE_URL;
    else process.env.MANGROVE_BASE_URL = previous;
  }
});

test('test keys require explicit routing and never default to production', () => {
  const previous = process.env.MANGROVE_BASE_URL;
  const environment = process.env.MANGROVE_ENVIRONMENT;
  delete process.env.MANGROVE_BASE_URL;
  delete process.env.MANGROVE_ENVIRONMENT;
  try {
    assert.throws(() => new MangroveAI({ apiKey: 'test_offline_fixture' }), ConfigurationError);
    assert.throws(() => new MangroveAI({ apiKey: 'test_offline_fixture', environment: 'prod' }), ConfigurationError);
    assert.equal(new MangroveAI({ apiKey: 'test_offline_fixture', environment: 'local' }).baseUrl, 'http://localhost:5001');
    assert.equal(new MangroveAI({ apiKey: 'test_offline_fixture', baseUrl: 'https://explicit-test.example.invalid' }).baseUrl, 'https://explicit-test.example.invalid');
    assert.equal(new MangroveAI({ apiKey: 'local_offline_fixture' }).baseUrl, 'http://localhost:5001');
  } finally {
    if (previous === undefined) delete process.env.MANGROVE_BASE_URL; else process.env.MANGROVE_BASE_URL = previous;
    if (environment === undefined) delete process.env.MANGROVE_ENVIRONMENT; else process.env.MANGROVE_ENVIRONMENT = environment;
  }
});

for (const baseUrl of ['http://example.com', 'https://user:password@example.com', 'https://example.com?key=secret', 'https://example.com/#fragment', 'https://example.com/unexpected']) {
  test(`refuses unsafe or ambiguous origin: ${baseUrl.split('?')[0]}`, () => assert.throws(() => new MangroveAI({ baseUrl }), ConfigurationError));
}

for (const timeoutMs of [0, -1, NaN, Infinity, 1.5]) {
  test(`refuses invalid timeout ${timeoutMs}`, () => assert.throws(() => new MangroveAI({ timeoutMs }), ConfigurationError));
}

test('missing credentials, missing path fields and dot segments fail before a request', async () => {
  let calls = 0;
  const fetcher = async () => { calls++; return json({}); };
  const old = process.env.MANGROVE_API_KEY;
  delete process.env.MANGROVE_API_KEY;
  try { await assert.rejects(new MangroveAI({ fetch: fetcher }).users.getMyMetrics(), ConfigurationError); }
  finally { if (old !== undefined) process.env.MANGROVE_API_KEY = old; }
  const sdk = client(fetcher);
  await assert.rejects(sdk.request('GET /api/v1/strategies/{strategy_id}', {}), ConfigurationError);
  await assert.rejects(sdk.request('GET /api/v1/strategies/{strategy_id}', { path: { strategy_id: '..' } }), ConfigurationError);
  await assert.rejects(sdk.request('GET /invented', {}), ConfigurationError);
  await assert.rejects(sdk.request('toString', {}), ConfigurationError);
  await assert.rejects(sdk.request('GET /api/v1/users/me/metrics', null), ConfigurationError);
  assert.equal(calls, 0);
});

test('path values are encoded once and caller query/body are preserved', async () => {
  const sdk = client(async (url, options) => {
    assert.equal(new URL(url).pathname, '/api/v1/strategies/a%2Fb%3Fsecret');
    assert.equal(options.method, 'PUT');
    assert.deepEqual(JSON.parse(options.body), { name: 'changed', position_size_calc: null });
    return json({ strategy: { id: 'fixture' } });
  });
  await sdk.request('PUT /api/v1/strategies/{strategy_id}', { path: { strategy_id: 'a/b?secret' }, body: { name: 'changed', position_size_calc: null } });
});

test('nonfinite JSON values are rejected instead of silently converted to null', async () => {
  const sdk = client(async () => { throw new Error('must not call'); });
  await assert.rejects(sdk.request('POST /api/v1/strategies/', { body: { name: 'x', value: NaN } }), ConfigurationError);
});

for (const field of ['Authorization', 'Host', 'Content-Length']) {
  test(`protected header ${field} cannot be replaced`, async () => {
    await assert.rejects(client(async () => json({})).request('GET /api/v1/users/me/metrics', { headers: { [field]: 'override' } }), ConfigurationError);
  });
}

test('session refresh uses explicit cookie+CSRF headers with no JSON body', async () => {
  const sdk = client(async (url, options) => {
    assert.equal(new URL(url).pathname, '/api/v1/auth/refresh');
    assert.equal(options.headers.get('Cookie'), 'mg_refresh=fixture; mg_csrf=csrf');
    assert.equal(options.headers.get('X-CSRF-Token'), 'csrf');
    assert.equal(options.body, undefined);
    return json(await fixture('refresh-success'));
  });
  const value = await sdk.request('POST /api/v1/auth/refresh', { headers: { Cookie: 'mg_refresh=fixture; mg_csrf=csrf', 'X-CSRF-Token': 'csrf' } });
  assert.equal(value.access_token, 'fixture_rotated_access_token');
});

test('API errors preserve safe status/code/correlation and never retry a POST', async () => {
  let calls = 0;
  const sdk = client(async () => { calls++; return json(await fixture('unavailable'), 503, { 'Retry-After': '3' }); });
  await assert.rejects(sdk.request('POST /api/v2/backtests/', { body: {} }), error => {
    assert.ok(error instanceof APIError);
    assert.equal(error.status, 503);
    assert.equal(error.code, 'SERVICE_UNAVAILABLE');
    assert.equal(error.correlationId, 'fixture-request');
    assert.equal(error.retryAfter, '3');
    return true;
  });
  assert.equal(calls, 1);
});

test('reflected credentials are redacted from error strings and JSON', async () => {
  const sdk = client(async () => json({ code: fakeKey, message: `Bearer ${fakeKey}`, correlation_id: fakeKey }, 401));
  await assert.rejects(sdk.users.getMyMetrics(), error => {
    assert.ok(error instanceof APIError);
    assert.ok(!String(error).includes(fakeKey));
    assert.ok(!JSON.stringify(error).includes(fakeKey));
    return true;
  });
});

test('client inspection does not reveal the private API credential', () => {
  const sdk = client(async () => json({}));
  assert.ok(!JSON.stringify(sdk).includes(fakeKey));
  assert.ok(!Object.values(sdk).includes(fakeKey));
});

test('reflected session credentials are redacted from messages and retained envelopes', async () => {
  const token = 'fixture_firebase_credential';
  const sdk = client(async () => json({ code: 'INVALID_LOGIN', message: `Cannot verify ${token}`, [token]: token }, 401));
  await assert.rejects(sdk.request('POST /api/v1/auth/login', { body: { firebase_token: token } }), error => {
    assert.ok(error instanceof APIError);
    assert.ok(!String(error).includes(token));
    assert.ok(!JSON.stringify(error.response).includes(token));
    return true;
  });
});

test('server policy and payment challenge remain inspectable without an automatic payer', async () => {
  let calls = 0;
  const request = { base_token: 'BTC', quote_token: 'USD', seed: 42, idempotency_key: 'fixture-operation' };
  const decision = { error: { code: 'POLICY_HOLD', message: 'Mangrove has held BTC/USD', details: { approved: false, snapshot_id: 'fixture-snapshot', ...request } } };
  const challenge = 'fixture-' + 'x'.repeat(900);
  await assert.rejects(client(async () => { calls++; return json(decision, 402, { 'Payment-Required': challenge }); }).request('POST /api/v2/backtests/', { body: request }), error => {
    assert.ok(error instanceof APIError);
    assert.deepEqual(error.response, decision);
    assert.equal(error.headers['payment-required'], challenge);
    assert.equal(JSON.stringify(error).includes('fixture-snapshot'), false);
    return true;
  });
  assert.equal(calls, 1);
});

test('canonical workflow forwards the request and preserves the server decision', async () => {
  const decision = { approved: false, reason: 'fixture-policy-hold', snapshot: { live_account: 'fixture' }, outcome: 'held' };
  const sdk = client(async (url, options) => {
    assert.equal(new URL(url).pathname, '/api/v1/strategy-workflow/get_strategy');
    assert.deepEqual(JSON.parse(options.body), { strategy_id: 'fixture-id' });
    return json(decision);
  });
  assert.deepEqual(await sdk.strategyWorkflow.getStrategy({ body: { strategy_id: 'fixture-id' } }), decision);
});

test('shared unauthorized fixture surfaces 401 rather than empty success', async () => {
  await assert.rejects(client(async () => json(await fixture('unauthorized'), 401)).users.getMyMetrics(), error => error instanceof APIError && error.status === 401);
});

for (const value of [{ success: false, metrics: {} }, { success: true }, { success: true, metrics: [] }, { success: true, metrics: { messages_count: '7' } }]) {
  test(`rejects malformed metrics: ${JSON.stringify(value)}`, async () => await assert.rejects(client(async () => json(value)).users.getMyMetrics(), MalformedResponseError));
}

test('HTML, invalid JSON and redirects cannot look like working API responses', async () => {
  for (const response of [new Response('<html>app</html>', { headers: { 'Content-Type': 'text/html' } }), new Response('{'), new Response('', { status: 302, headers: { Location: 'https://evil.example.invalid' } })]) {
    await assert.rejects(client(async () => response).users.getMyMetrics(), MalformedResponseError);
  }
});

test('declared and streamed body sizes are bounded', async () => {
  await assert.rejects(client(async () => json({}, 200, { 'Content-Length': '9999' }), { maxResponseBytes: 20 }).users.getMyMetrics(), MalformedResponseError);
  await assert.rejects(client(async () => json({ metrics: 'x'.repeat(100) }), { maxResponseBytes: 20 }).users.getMyMetrics(), MalformedResponseError);
});

test('unsupported stream media is refused and cancelled before consuming the body', async () => {
  let cancelled = false;
  const stream = new ReadableStream({ cancel() { cancelled = true; } });
  const sdk = client(async () => new Response(stream, { headers: { 'Content-Type': 'text/event-stream' } }));
  await assert.rejects(sdk.request('GET /api/v1/oracle/deployed/stream', {}), MalformedResponseError);
  assert.equal(cancelled, true);
});

test('deadline works even when an injected fetch ignores abort', async () => {
  await assert.rejects(client(async () => new Promise(() => {}), { timeoutMs: 10 }).users.getMyMetrics(), RequestTimeoutError);
});

test('caller cancellation aborts an in-flight request', async () => {
  const controller = new AbortController();
  const pending = client(async () => new Promise(() => {})).users.getMyMetrics({ signal: controller.signal });
  controller.abort();
  await assert.rejects(pending, RequestAbortedError);
});

test('signals pagination follows server next_offset rather than requested limit', async () => {
  const offsets = [];
  const sdk = client(async url => {
    const offset = Number(new URL(url).searchParams.get('offset'));
    offsets.push(offset);
    return json(await fixture(offset === 0 ? 'signals-page-one' : 'signals-page-two'));
  });
  const values = [];
  for await (const value of sdk.signals.listIter({ limit: 100 })) values.push(value.name);
  assert.deepEqual(offsets, [0, 1]);
  assert.deepEqual(values, ['fixture_one', 'fixture_two']);
});

test('a repeated or contradictory page raises rather than returning partial results', async () => {
  const sdk = client(async () => json(await fixture('signals-page-one')));
  await assert.rejects(async () => { for await (const ignored of sdk.signals.listIter()) void ignored; }, MalformedResponseError);
  const invalid = { ...await fixture('signals-page-one'), next_offset: null };
  await assert.rejects(client(async () => json(invalid)).signals.list(), MalformedResponseError);
});

test('polling preserves the server result and submits no extra work', async () => {
  let calls = 0;
  const completed = await fixture('backtest-completed');
  const sdk = client(async (url, options) => {
    assert.equal(options.method, 'GET');
    assert.ok(String(url).endsWith('/status'));
    return json(++calls === 1 ? await fixture('backtest-running') : completed);
  });
  assert.deepEqual(await sdk.backtesting.wait(completed.backtest_id, { pollIntervalMs: 1 }), completed);
  assert.equal(calls, 2);
});

test('polling is bounded and does not confuse failure with completion', async () => {
  const running = await fixture('backtest-running');
  const sdk = client(async () => json(running));
  await assert.rejects(sdk.backtesting.wait(running.backtest_id, { timeoutMs: 8, pollIntervalMs: 2 }), RequestTimeoutError);
  const failed = { ...running, status: 'failed', error_message: 'fixture engine failure' };
  assert.deepEqual(await client(async () => json(failed)).backtesting.wait(running.backtest_id), failed);
});

test('native fetch and installed first-call path work over isolated loopback HTTP', async () => {
  const value = await fixture('usage-success');
  const server = createServer((request, response) => {
    assert.equal(request.headers.authorization, `Bearer ${fakeKey}`);
    assert.equal(request.url, '/api/v1/users/me/metrics');
    response.writeHead(200, { 'Content-Type': 'application/json' });
    response.end(JSON.stringify(value));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const sdk = new MangroveAI({ apiKey: fakeKey, baseUrl: `http://127.0.0.1:${server.address().port}` });
    assert.deepEqual(await sdk.users.getMyMetrics(), value.metrics);
  } finally { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); }
});

test('native fetch deadline includes a stalled response body', async () => {
  const server = createServer((request, response) => {
    response.writeHead(200, { 'Content-Type': 'application/json' });
    response.write('{');
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try {
    const sdk = new MangroveAI({ apiKey: fakeKey, baseUrl: `http://127.0.0.1:${server.address().port}`, timeoutMs: 25 });
    await assert.rejects(sdk.users.getMyMetrics(), RequestTimeoutError);
  } finally { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); }
});
