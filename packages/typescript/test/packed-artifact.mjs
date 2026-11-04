import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const scratch = mkdtempSync(join(tmpdir(), 'mangrove-sdk-package-'));
const fixture = JSON.parse(readFileSync(join(packageRoot, '../../contracts/mangroveai/fixtures/usage-success.json'), 'utf8'));
const configFixture = JSON.parse(readFileSync(join(packageRoot, '../../contracts/mangroveai/fixtures/execution-config-success.json'), 'utf8'));
const localFixture = JSON.parse(readFileSync(join(packageRoot, '../../contracts/mangroveai/fixtures/local-deployment-not-ready.json'), 'utf8'));
const signalFixtures = ['one', 'two'].map(page => JSON.parse(readFileSync(join(packageRoot, `../../contracts/mangroveai/fixtures/signals-page-${page}.json`), 'utf8')));
let calls = 0;
let streamCalls = 0;
const backtestPaths = [];
const server = createServer((request, response) => {
  calls++;
  assert.equal(request.headers.authorization, 'Bearer prod_fixture_package_key');
  if (['/api/v1/backtests/', '/api/v1/backtests'].includes(request.url)) {
    assert.equal(request.method, 'POST');
    backtestPaths.push(request.url);
    let body = '';
    request.on('data', chunk => { body += chunk; });
    request.on('end', () => {
      assert.deepEqual(JSON.parse(body), { strategy_id: 'alias-fixture' });
      response.writeHead(200, { 'Content-Type': 'application/json' });
      response.end(JSON.stringify({ compatibility: true, server_decision: null }));
    });
    return;
  }
  if (request.url === '/api/v1/help/ask/stream') {
    streamCalls++;
    response.writeHead(200, { 'Content-Type': 'text/event-stream' });
    response.end('data: fixture\n\n');
    return;
  }
  if (request.url === '/api/v1/help/ask') {
    assert.equal(request.method, 'POST');
    response.writeHead(200, { 'Content-Type': 'application/json' });
    response.end(JSON.stringify({ session_id: localFixture.strategy_id, answer: 'Fixture answer', citations: [], confidence: 'normal' }));
    return;
  }
  assert.equal(request.method, 'GET');
  if (request.url === `/api/v1/strategies/${localFixture.strategy_id}/local-deployment?asset_class=equity`) {
    response.writeHead(409, { 'Content-Type': 'application/json', 'X-Correlation-Id': 'local-fixture-conflict' });
    response.end(JSON.stringify({ error: 'DEPLOYMENT_CONFLICT', message: 'Server validation decision' }));
    return;
  }
  const body = request.url === '/api/v1/users/me/metrics' ? fixture
    : request.url === '/api/v1/config/execution-config-schema' ? configFixture
    : request.url.startsWith('/api/v1/signals/?') ? signalFixtures[Number(new URL(request.url, 'http://localhost').searchParams.get('offset'))]
    : request.url === `/api/v1/strategies/${localFixture.strategy_id}/local-deployment?asset_class=crypto` ? localFixture
    : request.url === `/api/v1/help/conversations/${localFixture.strategy_id}` ? { session_id: localFixture.strategy_id, messages: [{ role: 'assistant', content: 'Fixture answer' }], message_count: 1 } : null;
  assert.ok(body, 'Unexpected request from installed package');
  response.writeHead(200, { 'Content-Type': 'application/json' });
  response.end(JSON.stringify(body));
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
try {
  const packed = JSON.parse(execFileSync('npm', ['pack', '--ignore-scripts', '--json', '--pack-destination', scratch], { cwd: packageRoot, encoding: 'utf8' }))[0];
  const sourcePackage = JSON.parse(readFileSync(join(packageRoot, 'package.json'), 'utf8'));
  assert.equal(packed.name, '@mangrove-ai/sdk');
  assert.equal(packed.version, sourcePackage.version);
  assert.match(packed.version, /^[1-9]\d*\./);
  writeFileSync(join(scratch, 'package.json'), JSON.stringify({ private: true, type: 'module' }));
  execFileSync('npm', ['install', '--ignore-scripts', '--no-audit', '--no-fund', join(scratch, packed.filename)], { cwd: scratch, stdio: 'pipe' });
  const installedPackage = JSON.parse(readFileSync(join(scratch, 'node_modules/@mangrove-ai/sdk/package.json'), 'utf8'));
  assert.equal(installedPackage.name, packed.name);
  assert.equal(installedPackage.version, packed.version);
  writeFileSync(join(scratch, 'local-fixture.json'), JSON.stringify(localFixture));
  writeFileSync(join(scratch, 'smoke.mjs'), `
    import assert from 'node:assert/strict';
    import { readFileSync } from 'node:fs';
    import { MangroveAI, APIError, ConfigurationError } from '@mangrove-ai/sdk';
    const sdk = new MangroveAI({apiKey:'prod_fixture_package_key',baseUrl:process.env.SDK_FIXTURE_ORIGIN});
    const metrics = await sdk.users.getMyMetrics();
    assert.equal(metrics.messages_count,7);
    const config = await sdk.request('GET /api/v1/config/execution-config-schema', {});
    assert.equal(config.json_schema.$schema,'https://json-schema.org/draft/2020-12/schema');
    assert.equal(config.json_schema.properties.cooldown_config,undefined);
    assert.equal(config.param_glossary.cooldown_config,undefined);
    assert.equal(config.defaults.cooldown_config,undefined);
    assert.equal(config.defaults.cooldown_model,'trades');
    assert.equal(config.json_schema.properties.circuit_breaker.additionalProperties,false);
    assert.equal(config.param_glossary.circuit_breaker.fields.consecutive_loss_limit.type,'int');
    assert.ok(import.meta.resolve('@mangrove-ai/sdk').includes('/node_modules/'));
    const signals = [];
    for await (const item of sdk.signals.listIter({limit:1})) signals.push(item);
    assert.deepEqual(signals.map(row => [row.evaluation_mode,row.data_provider]), [['frame',null],['live','x']]);
    const localFixture = JSON.parse(readFileSync('local-fixture.json', 'utf8'));
    assert.deepEqual(await sdk.strategies.localDeployment(localFixture.strategy_id, {assetClass:'crypto'}), localFixture);
    await assert.rejects(sdk.strategies.localDeployment(localFixture.strategy_id, {assetClass:'equity'}), error => {
      assert.ok(error instanceof APIError);
      assert.equal(error.status,409);
      assert.equal(error.correlationId,'local-fixture-conflict');
      return true;
    });
    for (const key of ['POST /api/v1/backtests/', 'POST /api/v1/backtests']) {
      assert.deepEqual(await sdk.request(key, {body:{strategy_id:'alias-fixture'}}), {compatibility:true,server_decision:null});
    }
    const answer = await sdk.request('POST /api/v1/help/ask', { body: { message: 'Fixture question' } });
    assert.equal(answer.answer, 'Fixture answer');
    assert.deepEqual(answer.citations, []);
    const conversation = await sdk.request('GET /api/v1/help/conversations/{session_id}', { path: { session_id: localFixture.strategy_id } });
    assert.equal(conversation.message_count, 1);
    await assert.rejects(sdk.request('POST /api/v1/help/ask/stream', { body: { message: 'Fixture question' } }), ConfigurationError);
    await assert.rejects(sdk.request("GET /api/v1/auth/login/google", {}), ConfigurationError);
    console.log('Packed usage/configuration/local snapshot/HelpBot JSON and preflight stream checks passed');
  `);
  const { spawn } = await import('node:child_process');
  const child = spawn(process.execPath, ['smoke.mjs'], { cwd: scratch, env: { ...process.env, SDK_FIXTURE_ORIGIN: `http://127.0.0.1:${server.address().port}` }, stdio: 'inherit' });
  const exitCode = await new Promise(resolve => child.once('exit', resolve));
  assert.equal(exitCode, 0);
  assert.equal(calls, 10);
  assert.deepEqual(backtestPaths, ['/api/v1/backtests/', '/api/v1/backtests']);
  assert.equal(streamCalls, 0);
} finally {
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
  rmSync(scratch, { recursive: true, force: true });
}
