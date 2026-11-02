import assert from 'node:assert/strict';
import test from 'node:test';
import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { MIGRATION_NOTICE } from '../../../scripts/complete_typescript_release.mjs';

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
    const result = spawnSync(process.execPath, ['--import', preload, controller], { cwd, encoding: 'utf8', timeout: 10000, env: { PATH: process.env.PATH, DRY_RUN: 'false', PUBLISH_SUCCEEDED: 'true', UPLOAD_ACCEPTED: settings.acceptedUpload === false ? 'false' : 'true', EXPECTED_VERSION: '1.1.0', RELEASE_ARTIFACT: join(cwd, 'artifact.json'), GITHUB_TOKEN: 'offline-fixture' } });
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

const targets = ['0.1.2', '0.2.0', '0.3.0'].map(version => `@mangrove-ai/sdk@${version}`);
const correctNotices = Object.fromEntries(targets.map(target => [target, MIGRATION_NOTICE]));
const deprecations = observed => observed.commands.filter(call => call.args[0] === 'deprecate');

test('combined CLI waits for accepted metadata and tarball, then leaves matching notices untouched on repeated completion', () => {
  for (const settings of [{ metadata404s: 5, archive404s: 1 }, { acceptedUpload: false }]) {
    const { result, observed } = run({ ...settings, notices: correctNotices });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(observed.clock, settings.acceptedUpload === false ? 0 : 180000);
    assert.deepEqual(deprecations(observed), []);
    assert.deepEqual(observed.commands.map(call => call.args[1]), targets);
    assert.ok(observed.requests.every(call => call.method === 'GET'));
    const receipt = JSON.parse(result.stdout);
    assert.equal(receipt.githubRelease.source_sha, 'a'.repeat(40));
    assert.equal(receipt.version, '1.1.0');
  }
});

test('combined CLI updates only exact mismatched notices after verified assets; repeat writes nothing', () => {
  const first = run({ acceptedUpload: false, notices: { ...correctNotices, [targets[1]]: 'older notice', [targets[2]]: '' } });
  assert.equal(first.result.status, 0, first.result.stderr);
  assert.deepEqual(deprecations(first.observed).map(call => call.args[1]), targets.slice(1));
  assert.ok(deprecations(first.observed).every(call => call.args[2] === MIGRATION_NOTICE));
  assert.ok(first.observed.requests.every(call => call.method === 'GET'));
  const second = run({ acceptedUpload: false, notices: first.observed.notices });
  assert.equal(second.result.status, 0, second.result.stderr);
  assert.deepEqual(deprecations(second.observed), []);
  assert.ok(second.observed.requests.every(call => call.method === 'GET'));
});

for (const [name, settings] of Object.entries({
  'source conflict': { metadataSource: 'c'.repeat(40) },
  'integrity conflict': { metadataIntegrity: 'sha512-Y29uZmxpY3Q=' },
  'archive checksum conflict': { archiveCorrupt: true },
  'tag source conflict': { tagSource: 'c'.repeat(40) },
  'lightweight tag': { tagType: 'commit' },
  'release body conflict': { releaseBody: 'wrong release' },
  'asset digest conflict': { assetDigestConflict: true },
  'asset bytes conflict': { assetBytesConflict: true },
  'registry authentication failure': { registryStatus: 401 },
  'registry rate limit': { registryStatus: 429 },
  'registry network failure': { registryNetworkError: true },
  'archive authentication failure': { archiveStatus: 403 },
  'archive rate limit': { archiveStatus: 429 },
  'archive network failure': { archiveNetworkError: true },
  'GitHub authentication failure': { githubStatus: 403 },
  'GitHub rate limit': { githubStatus: 429 },
  'GitHub network failure': { githubNetworkError: true },
  'notice query failure': { noticeError: true },
  'visibility timeout': { metadata404s: 99 },
  'shared metadata and archive timeout': { metadata404s: 19, archive404s: 99 },
  'existing publication ordinary404': { acceptedUpload: false, metadata404s: 1 },
})) {
  test(`combined CLI aborts ${name} without publication or notice writes`, () => {
    const { result, observed } = run({ ...settings, notices: correctNotices });
    assert.notEqual(result.status, 0, result.stderr);
    assert.deepEqual(deprecations(observed), []);
    assert.ok(observed.requests.every(call => call.method === 'GET'));
    if (settings.registryStatus || settings.registryNetworkError || settings.archiveStatus || settings.archiveNetworkError || settings.acceptedUpload === false) assert.equal(observed.clock, 0);
    if (name.includes('timeout')) assert.equal(observed.clock, 600000);
  });
}
