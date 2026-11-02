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
let calls = 0;
const server = createServer((request, response) => {
  calls++;
  assert.equal(request.method, 'GET');
  assert.equal(request.headers.authorization, 'Bearer prod_fixture_package_key');
  const body = request.url === '/api/v1/users/me/metrics' ? fixture
    : request.url === '/api/v1/config/execution-config-schema' ? configFixture : null;
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
  writeFileSync(join(scratch, 'smoke.mjs'), `
    import assert from 'node:assert/strict';
    import { MangroveAI } from '@mangrove-ai/sdk';
    const sdk = new MangroveAI({apiKey:'prod_fixture_package_key',baseUrl:process.env.SDK_FIXTURE_ORIGIN});
    const metrics = await sdk.users.getMyMetrics();
    assert.equal(metrics.messages_count,7);
    const config = await sdk.request('GET /api/v1/config/execution-config-schema', {});
    assert.equal(config.json_schema.$schema,'https://json-schema.org/draft/2020-12/schema');
    assert.equal(config.json_schema.properties.cooldown_config.additionalProperties.properties.short_window_bars.type,'integer');
    assert.ok(config.param_glossary.cooldown_config.required_fields.includes('short_window_bars'));
    assert.ok(import.meta.resolve('@mangrove-ai/sdk').includes('/node_modules/'));
    console.log('Packed artifact usage and execution configuration examples passed');
  `);
  const { spawn } = await import('node:child_process');
  const child = spawn(process.execPath, ['smoke.mjs'], { cwd: scratch, env: { ...process.env, SDK_FIXTURE_ORIGIN: `http://127.0.0.1:${server.address().port}` }, stdio: 'inherit' });
  const exitCode = await new Promise(resolve => child.once('exit', resolve));
  assert.equal(exitCode, 0);
  assert.equal(calls, 2);
} finally {
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
  rmSync(scratch, { recursive: true, force: true });
}
