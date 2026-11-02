import assert from 'node:assert/strict';
import test from 'node:test';
import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const controller = fileURLToPath(new URL('../../../scripts/complete_typescript_release.mjs', import.meta.url));
const preload = fileURLToPath(new URL('./fixtures/release-completion-preload.mjs', import.meta.url));

function run(settings) {
  const cwd = mkdtempSync(join(tmpdir(), 'sdk-release-cli-'));
  try {
    mkdirSync(join(cwd, 'packages/typescript'), { recursive: true });
    const manifest = { name: '@mangrove-ai/sdk', version: '1.1.0', repository: { url: 'https://github.com/MangroveTechnologies/MangroveAI-SDK.git', directory: 'packages/typescript' } };
    const bytes = Buffer.from('offline original release artifact');
    const artifact = { name: manifest.name, version: manifest.version, sourceSha: 'a'.repeat(40), filename: 'mangrove-ai-sdk-1.1.0.tgz', sha256: createHash('sha256').update(bytes).digest('hex'), integrity: `sha512-${createHash('sha512').update(bytes).digest('base64')}` };
    writeFileSync(join(cwd, artifact.filename), bytes);
    for (const [name, data] of [['packages/typescript/package.json', manifest], ['packages/typescript/package-lock.json', { ...manifest, packages: { '': manifest } }], ['artifact.json', artifact], ['scenario.json', settings]]) writeFileSync(join(cwd, name), JSON.stringify(data));
    const result = spawnSync(process.execPath, ['--import', preload, controller], { cwd, encoding: 'utf8', timeout: 10000, env: { PATH: process.env.PATH, DRY_RUN: 'false', PUBLISH_SUCCEEDED: 'true', UPLOAD_ACCEPTED: 'true', EXPECTED_VERSION: '1.1.0', RELEASE_ARTIFACT: join(cwd, 'artifact.json'), GITHUB_TOKEN: 'offline-fixture' } });
    return { result, observed: JSON.parse(readFileSync(join(cwd, 'observed.json'), 'utf8')) };
  } finally { rmSync(cwd, { recursive: true, force: true }); }
}

test('actual release CLI starts the bounded GitHub budget after accepted-upload visibility', () => {
  const { result, observed } = run({ metadata404s: 5 });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(observed.clock, 150000);
  assert.equal(observed.metadataReads, 6);
  const github = observed.requests.filter(call => call.host === 'api.github.com');
  assert.ok(github.length > 0);
  assert.ok(github.every(call => call.at === 150000 && !call.aborted && call.method === 'GET'));
  assert.ok(observed.commands.every(call => call.command === 'npm' && ['view', 'deprecate'].includes(call.args[0])));
  assert.ok(observed.commands.filter(call => call.args[0] === 'deprecate').every(call => ['0.1.2', '0.2.0', '0.3.0'].some(version => call.args[1] === `@mangrove-ai/sdk@${version}`)));
});

test('actual release CLI still aborts GitHub work after its own two-minute budget', () => {
  const { result, observed } = run({ metadata404s: 5, githubDelay: 120001 });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /TimeoutError|fixture timeout/);
  assert.equal(observed.requests.find(call => call.host === 'api.github.com').aborted, true);
  assert.deepEqual(observed.commands, []);
});
