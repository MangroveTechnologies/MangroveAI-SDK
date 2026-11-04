import assert from 'node:assert/strict';
import test from 'node:test';
import { MangroveAI } from '../dist/index.js';

test('token unlocks preserve a byte-shortened cursor without automatically reading another page', async () => {
  const seen = [];
  const rows = [{ token: 'synthetic-A', schedule: [{ amount: '42.5' }] }, { token: 'synthetic-B', schedule: [] }];
  const sdk = new MangroveAI({
    apiKey: 'test_fixture', baseUrl: 'https://fixture.invalid',
    fetch: async (url, options) => {
      const request = new URL(url);
      assert.equal(request.pathname, '/api/v1/defi/token-unlocks');
      assert.equal(options.method, 'GET');
      assert.equal(options.headers.get('Authorization'), 'Bearer test_fixture');
      seen.push(Object.fromEntries(request.searchParams));
      const offset = Number(request.searchParams.get('offset'));
      const page = [rows[offset]];
      return new Response(JSON.stringify({
        success: true, provider: 'defillama', count: 1, data: page, records: page,
        total_count: 2, limit: 20, offset, has_more: offset === 0,
        next_offset: offset === 0 ? 1 : null,
      }), { headers: { 'Content-Type': 'application/json' } });
    },
  });
  const first = await sdk.request('GET /api/v1/defi/token-unlocks', { query: { limit: 20, offset: 0 } });
  assert.equal(seen.length, 1);
  assert.equal(first.count, 1);
  assert.equal(first.total_count, 2);
  assert.deepEqual(first.data, first.records);
  assert.deepEqual(first.data, [rows[0]]);
  assert.equal(first.next_offset, 1);
  const last = await sdk.request('GET /api/v1/defi/token-unlocks', {
    query: { limit: 20, offset: first.next_offset },
  });
  assert.deepEqual(last.data, [rows[1]]);
  assert.equal(last.has_more, false);
  assert.equal(last.next_offset, null);
  assert.deepEqual(seen, [{ limit: '20', offset: '0' }, { limit: '20', offset: '1' }]);
});
