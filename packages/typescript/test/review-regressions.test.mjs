import assert from 'node:assert/strict';
import test from 'node:test';
import { MangroveAI, APIError, MalformedResponseError } from '../dist/index.js';

const json = (value, status = 200) => new Response(JSON.stringify(value), {
  status, headers: { 'Content-Type': 'application/json' },
});

for (const later of [
  [{ name: 'first', category: 'fixture' }],
  [{ name: 'new', category: 'fixture' }, { name: 'first', category: 'changed', usage_count: 2 }],
]) {
  test(`advancing signal pages reject repeated identities before yielding later rows (${later.length})`, async () => {
    let calls = 0;
    const sdk = new MangroveAI({ apiKey: 'prod_fixture_review_only', fetch: async url => {
      const offset = Number(new URL(url).searchParams.get('offset'));
      calls++;
      return json({ signals: offset === 0 ? [{ name: 'first', category: 'fixture' }] : later,
        total: 1 + later.length, offset, limit: later.length, has_more: offset === 0,
        next_offset: offset === 0 ? 1 : null });
    } });
    const names = [];
    await assert.rejects(async () => {
      for await (const signal of sdk.signals.listIter()) names.push(signal.name);
    }, MalformedResponseError);
    assert.deepEqual(names, ['first']);
    assert.equal(calls, 2);
  });
}

test('duplicate identities within a signal page are rejected before any row is yielded', async () => {
  const sdk = new MangroveAI({ apiKey: 'prod_fixture_review_only', fetch: async () => json({
    signals: [{ name: 'same', category: 'fixture' }, { name: 'same', category: 'fixture' }],
    total: 2, offset: 0, limit: 2, has_more: false, next_offset: null,
  }) });
  const names = [];
  await assert.rejects(async () => {
    for await (const signal of sdk.signals.listIter()) names.push(signal.name);
  }, MalformedResponseError);
  assert.deepEqual(names, []);
});

test('distinct signal identities with identical other fields retain server order', async () => {
  let calls = 0;
  const sdk = new MangroveAI({ apiKey: 'prod_fixture_review_only', fetch: async url => {
    const offset = Number(new URL(url).searchParams.get('offset'));
    calls++;
    return json({ signals: [{ name: offset === 0 ? 'first' : 'second', category: 'fixture' }],
      total: 2, offset, limit: 1, has_more: offset === 0, next_offset: offset === 0 ? 1 : null });
  } });
  const names = [];
  for await (const signal of sdk.signals.listIter({ limit: 1 })) names.push(signal.name);
  assert.deepEqual(names, ['first', 'second']);
  assert.equal(calls, 2);
});

for (const token of ['1', 'true', 'null', '401', 'fixture_"quoted"_\\_token']) {
  test(`structured error redaction preserves JSON primitives (${JSON.stringify(token)})`, async () => {
    let calls = 0;
    const sdk = new MangroveAI({ apiKey: 'prod_fixture_review_only', fetch: async () => {
      calls++;
      return json({ code: 'INVALID_LOGIN', message: `Cannot verify ${token}`, http_status: 401,
        details: { [`echo_${token}`]: [token, 401, true, null, { session_token: token }],
          approved: false, zero: 0, empty: null, nested: [{ http_status: 401 }] } }, 401);
    } });
    await assert.rejects(sdk.request('POST /api/v1/auth/login', { body: { firebase_token: token } }), error => {
      assert.ok(error instanceof APIError);
      assert.equal(error.status, 401);
      assert.equal(error.code, 'INVALID_LOGIN');
      assert.equal(error.message, 'Cannot verify [redacted]');
      assert.equal(error.response.http_status, 401);
      assert.deepEqual(error.response.details, {
        'echo_[redacted]': ['[redacted]', 401, true, null, { session_token: '[redacted]' }],
        approved: false, zero: 0, empty: null, nested: [{ http_status: 401 }],
      });
      return true;
    });
    assert.equal(calls, 1);
  });
}
