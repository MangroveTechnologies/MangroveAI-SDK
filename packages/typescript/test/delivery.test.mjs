import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { ConfigurationError, MangroveAI } from '../dist/index.js';
import { operationMetadata, compatibilityOperationMetadata } from '../dist/contract.generated.js';

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const root = resolve(packageRoot, '../..');

test('declared HelpBot SSE refuses before starting a request', async () => {
  let calls = 0;
  const client = new MangroveAI({ apiKey: 'prod_delivery_fixture', fetch: async () => {
    calls++;
    return new Response('data: fixture\n\n', { headers: { 'content-type': 'text/event-stream' } });
  } });
  const error = await client.request('POST /api/v1/help/ask/stream', { body: { message: 'Fixture question' } }).catch(error => error);
  assert.equal(calls, 0, 'Unsupported streaming must not start server work');
  assert.ok(error instanceof ConfigurationError);
});

test('declared redirect-only flow refuses before a request', async () => {
  const coverage = JSON.parse(readFileSync(join(root, 'contracts/mangroveai/coverage.json'), 'utf8'));
  const operation = coverage.operations.find(item => item.typescript_transport === 'separate-redirect-flow-required').operation;
  let calls = 0;
  const client = new MangroveAI({ apiKey: 'prod_delivery_fixture', fetch: async () => {
    calls++;
    return new Response('{}', { headers: { 'content-type': 'application/json' } });
  } });
  const error = await client.request(operation, { body: {} }).catch(error => error);
  assert.equal(calls, 0, 'Unsupported redirects must not start server work');
  assert.ok(error instanceof ConfigurationError);
});

test('generated classification keeps mixed JSON success and opaque operations usable', async () => {
  const parent = join(packageRoot, '.contract-tests');
  mkdirSync(parent, { recursive: true });
  const scratch = mkdtempSync(join(parent, 'delivery-'));
  try {
    for (const path of ['contracts/mangroveai', 'scripts/generate_typescript_contract.py', 'packages/typescript/src',
      'packages/typescript/package.json', 'packages/typescript/tsconfig.json', 'src/mangrove_ai/_services']) {
      mkdirSync(dirname(join(scratch, path)), { recursive: true });
      cpSync(join(root, path), join(scratch, path), { recursive: true });
    }
    const source = join(scratch, 'contracts/mangroveai/openapi.json');
    const schema = JSON.parse(readFileSync(source, 'utf8'));
    schema.paths['/api/v1/users/me/metrics'].get.responses['302'] = { description: 'Optional redirect' };
    schema.paths['/api/v1/fixture/opaque'] = { get: { responses: { default: { description: 'Opaque declaration' } } } };
    writeFileSync(source, JSON.stringify(schema));
    const provenancePath = join(scratch, 'contracts/mangroveai/provenance.json');
    const provenance = JSON.parse(readFileSync(provenancePath, 'utf8'));
    provenance.contracts.find(item => item.path === 'openapi.json').sha256 = createHash('sha256').update(readFileSync(source)).digest('hex');
    provenance.source_dirty = true;
    writeFileSync(provenancePath, JSON.stringify(provenance));
    const generated = spawnSync('python3', ['scripts/generate_typescript_contract.py'], { cwd: scratch, encoding: 'utf8' });
    assert.equal(generated.status, 0, generated.stderr);
    const compiled = spawnSync(process.execPath, [join(packageRoot, 'node_modules/typescript/bin/tsc'), '-p', 'tsconfig.json'], {
      cwd: join(scratch, 'packages/typescript'), encoding: 'utf8',
    });
    assert.equal(compiled.status, 0, compiled.stdout + compiled.stderr);
    const candidate = await import(join(scratch, 'packages/typescript/dist/index.js'));
    const candidateMetadata = (await import(join(scratch, 'packages/typescript/dist/contract.generated.js'))).operationMetadata;
    for (const operation of ['GET /api/v1/users/me/metrics', 'GET /api/v1/fixture/opaque']) {
      assert.equal(candidateMetadata[operation].transport, 'json-or-no-content');
      let calls = 0;
      const client = new candidate.MangroveAI({ apiKey: 'prod_delivery_fixture', fetch: async () => {
        calls++;
        return new Response('{"preserved":null}', { headers: { 'content-type': 'application/json' } });
      } });
      assert.deepEqual(await client.request(operation, {}), { preserved: null });
      assert.equal(calls, 1);
    }
    const coverage = JSON.parse(readFileSync(join(scratch, 'contracts/mangroveai/coverage.json'), 'utf8'));
    for (const row of coverage.operations) assert.equal(candidateMetadata[row.operation].transport, row.typescript_transport);
    assert.equal(operationMetadata['POST /api/v1/help/ask/stream'].transport, 'separate-stream-or-non-json-client-required');
    delete schema.paths['/api/v1/backtests'];
    writeFileSync(source, JSON.stringify(schema));
    provenance.contracts.find(item => item.path === 'openapi.json').sha256 = createHash('sha256').update(readFileSync(source)).digest('hex');
    writeFileSync(provenancePath, JSON.stringify(provenance));
    const missingTarget = spawnSync('python3', ['scripts/generate_typescript_contract.py'], { cwd: scratch, encoding: 'utf8' });
    assert.notEqual(missingTarget.status, 0);
    assert.match(missingTarget.stderr, /Released backtest compatibility target is absent/);
  } finally { rmSync(scratch, { recursive: true, force: true }); }
});

// Public 1.1.0 accepted this key; upstream now declares only its unslashed twin.
test('released slashed backtest key preserves its HTTP request as a compatibility alias', async () => {
  assert.deepEqual(Object.keys(compatibilityOperationMetadata), ['POST /api/v1/backtests/']);
  assert.deepEqual(compatibilityOperationMetadata['POST /api/v1/backtests/'], { ...operationMetadata['POST /api/v1/backtests'], path:'/api/v1/backtests/' });
  const requests = [];
  const client = new MangroveAI({apiKey:'prod_alias_fixture', fetch:async (url, init) => {
    requests.push({url:String(url), method:init.method, authorization:new Headers(init.headers).get('authorization'), body:JSON.parse(init.body)});
    return new Response('{"server_decision":"preserved"}', {headers:{'content-type':'application/json'}});
  }});
  assert.deepEqual(await client.request('POST /api/v1/backtests/', {body:{strategy_id:'fixture'}}), {server_decision:'preserved'});
  assert.deepEqual(requests,[{url:'https://api.mangrovedeveloper.ai/api/v1/backtests/',method:'POST',authorization:'Bearer prod_alias_fixture',body:{strategy_id:'fixture'}}]);
  const coverage=JSON.parse(readFileSync(join(root,'contracts/mangroveai/coverage.json'),'utf8'));
  assert.ok(!coverage.operations.some(row=>row.operation==='POST /api/v1/backtests/'));
  assert.ok(coverage.operations.some(row=>row.operation==='POST /api/v1/backtests'));
  assert.deepEqual(coverage.compatibility_aliases, [{operation:'POST /api/v1/backtests/',canonical_operation:'POST /api/v1/backtests'}]);
  await assert.rejects(client.request('POST /api/v1/backtests//', {body:{}}), ConfigurationError);
  assert.equal(requests.length,1);
});
