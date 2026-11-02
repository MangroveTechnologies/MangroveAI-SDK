import assert from 'node:assert/strict';
import test from 'node:test';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { checkTypeScriptRelease } from '../../../scripts/check_typescript_release.mjs';

const mainSha = 'a'.repeat(40);
const identity = (name = '@mangrove-ai/sdk', version = '1.0.0') => ({
  manifest: { name, version, repository: { url: 'https://github.com/MangroveTechnologies/MangroveAI-SDK.git', directory: 'packages/typescript' } },
  lock: { name, version, packages: { '': { name, version } } },
  version, currentMainSha: mainSha, workflowSha: mainSha, artifact: { sourceSha: mainSha },
});
const response = (status, body) => ({ status, json: async () => body });
const noNetwork = async () => { throw new Error('Local identity rejection must precede registry calls'); };

test('release preflight binds the new AI package/version and refuses redirects', async () => {
  const seen = [];
  const result = await checkTypeScriptRelease({ ...identity(), request: async (url, options) => {
    seen.push(url); assert.equal(options.redirect, 'error'); assert.ok(options.signal); return response(404);
  } });
  assert.equal(result.name, '@mangrove-ai/sdk');
  assert.deepEqual(seen, ['https://registry.npmjs.org/%40mangrove-ai%2Fsdk/1.0.0']);
});
test('another package cannot be released from the AI repository', async () => {
  for (const name of ['@mangrove-ai/client', '@mangrove-ai/markets']) {
    await assert.rejects(checkTypeScriptRelease({ ...identity(name), request: noNetwork }), /only @mangrove-ai\/sdk/);
  }
});
test('historical Markets 0.x identity cannot be published as the AI product', async () => {
  await assert.rejects(checkTypeScriptRelease({ ...identity('@mangrove-ai/sdk', '0.3.0'), request: noNetwork }), /historical Markets/);
});
test('selected version must match reviewed source', async () => {
  await assert.rejects(checkTypeScriptRelease({ ...identity(), version: '1.0.1', request: noNetwork }), /Input version/);
});
test('lock name and both lock versions must match the source package', async () => {
  for (const edit of [value => value.lock.name = '@mangrove-ai/client', value => value.lock.version = '0.1.0', value => value.lock.packages[''].name = '@mangrove-ai/markets', value => value.lock.packages[''].version = '0.3.0']) {
    const value = identity(); edit(value); await assert.rejects(checkTypeScriptRelease({ ...value, request: noNetwork }), /package-lock/);
  }
});
test('wrong repository metadata cannot release the AI identity', async () => {
  const value = identity(); value.manifest.repository.url = 'https://github.com/MangroveTechnologies/MangroveMarkets';
  await assert.rejects(checkTypeScriptRelease({ ...value, request: noNetwork }), /repository/);
});
test('registry conflicts and unavailable responses stop publication', async () => {
  for (const status of [200, 302, 401, 500]) {
    await assert.rejects(checkTypeScriptRelease({ ...identity(), request: async () => response(status) }), /Existing publication|preflight failed/);
  }
});
test('publishing the AI product requires the new Markets package first', async () => {
  await assert.rejects(checkTypeScriptRelease({ ...identity(), requireMarketsRelease: true, request: async () => response(404) }), /Publish and verify/);
});
test('Markets prerequisite checks registry name/version/repository rather than status alone', async () => {
  const valid = { name: '@mangrove-ai/markets', version: '0.4.0', repository: { url: 'git+https://github.com/MangroveTechnologies/MangroveMarkets.git' } };
  for (const body of [valid, { ...valid, name: '@mangrove-ai/sdk' }, { ...valid, version: '0.3.0' }, { ...valid, repository: { url: 'https://github.com/other/repo' } }]) {
    const value = checkTypeScriptRelease({ ...identity(), requireMarketsRelease: true, request: async url => url.includes('%2Fsdk/') ? response(404) : response(200, body) });
    if (body === valid) assert.equal((await value).marketsReleaseRequired, true);
    else await assert.rejects(value, /Markets registry metadata/);
  }
});

test('an exact existing artifact resumes without another publication', async () => {
  const sourceSha = 'a'.repeat(40); const bytes = Buffer.from('fixture artifact');
  const artifact = { sourceSha, integrity: `sha512-${createHash('sha512').update(bytes).digest('base64')}`, sha256: createHash('sha256').update(bytes).digest('hex') };
  const data = { ...identity().manifest, gitHead: sourceSha, dist: { integrity: artifact.integrity, tarball: 'https://registry.npmjs.org/@mangrove-ai/sdk/-/sdk-1.0.0.tgz' } };
  const request = body => async url => url.endsWith('.tgz') ? new Response(bytes) : response(200, body);
  const result = await checkTypeScriptRelease({ ...identity(), artifact, request: request(data) });
  assert.equal(result.publishRequired, false);
  for (const change of [{ gitHead: 'b'.repeat(40) }, { dist: { integrity: 'sha512-b3RoZXI=' } }, { name: '@mangrove-ai/markets' }]) {
    await assert.rejects(checkTypeScriptRelease({ ...identity(), artifact, request: request({ ...data, ...change }) }), /conflicts/);
  }
});

test('a stale main ancestor cannot start an absent new version but can resume an exact existing artifact', async () => {
  const old = 'b'.repeat(40);
  await assert.rejects(checkTypeScriptRelease({ ...identity(), artifact: { sourceSha: old }, requireMarketsRelease: true, request: async () => response(404) }), /recovery-only/);
  const bytes = Buffer.from('old published artifact');
  const artifact = { sourceSha: old, integrity: `sha512-${createHash('sha512').update(bytes).digest('base64')}`, sha256: createHash('sha256').update(bytes).digest('hex') };
  const data = { ...identity().manifest, gitHead: old, dist: { integrity: artifact.integrity, tarball: 'https://registry.npmjs.org/@mangrove-ai/sdk/-/sdk-1.0.0.tgz' } };
  const markets = { name: '@mangrove-ai/markets', version: '0.4.0', repository: 'https://github.com/MangroveTechnologies/MangroveMarkets' };
  const result = await checkTypeScriptRelease({ ...identity(), artifact, requireMarketsRelease: true, request: async url => url.endsWith('.tgz') ? new Response(bytes) : response(200, url.includes('%2Fmarkets/') ? markets : data) });
  assert.equal(result.publishRequired, false);
  const current = await checkTypeScriptRelease({ ...identity(), requireMarketsRelease: true, request: async url => response(url.includes('%2Fmarkets/') ? 200 : 404, markets) });
  assert.equal(current.publishRequired, true);
});

test('new publication rejects fresh main when npm provenance would identify an older workflow source', async () => {
  let publications = 0;
  await assert.rejects(async () => {
    const result = await checkTypeScriptRelease({ ...identity(), workflowSha: 'b'.repeat(40), requireMarketsRelease: true, request: async url => response(url.includes('%2Fmarkets/') ? 200 : 404, { name: '@mangrove-ai/markets', version: '0.4.0', repository: 'https://github.com/MangroveTechnologies/MangroveMarkets' }) });
    if (result.publishRequired) publications += 1;
  }, /workflow.*provenance/i);
  assert.equal(publications, 0);
});

test('the actual publish shell rejects mismatched workflow provenance before invoking npm', () => {
  const workflow = readFileSync(new URL('../../../.github/workflows/typescript-release.yml', import.meta.url), 'utf8');
  const script = workflow.match(/- name: Publish new reviewed package[\s\S]*?        run: \|\n([\s\S]*?)        working-directory:/)?.[1].replace(/^          /gm, '');
  assert.ok(script, 'The native publisher run block must be available');
  const fixture = mkdtempSync(join(process.cwd(), '.release-publish-fixture-'));
  const log = join(fixture, 'npm-calls');
  try {
    writeFileSync(join(fixture, 'git'), '#!/bin/sh\nif [ "$1" = "rev-parse" ]; then printf "%s\\n" "$FIXTURE_MAIN_SHA"; fi\n', { mode: 0o700 });
    writeFileSync(join(fixture, 'npm'), '#!/bin/sh\nprintf "%s\\n" "$*" >> "$PUBLISH_LOG"\n', { mode: 0o700 });
    const run = (workflowSha, currentMainSha = mainSha) => spawnSync('bash', ['-e', '-c', script], { encoding: 'utf8', env: { PATH: fixture + ':' + process.env.PATH, SOURCE_SHA: mainSha, GITHUB_SHA: workflowSha, FIXTURE_MAIN_SHA: currentMainSha, NODE_AUTH_TOKEN: 'offline-fixture', PUBLISH_LOG: log } });
    const mismatch = run('b'.repeat(40));
    assert.notEqual(mismatch.status, 0); assert.match(mismatch.stdout, /workflow.*provenance/i); assert.equal(existsSync(log), false);
    assert.notEqual(run(mainSha, 'c'.repeat(40)).status, 0); assert.equal(existsSync(log), false);
    const sameSource = run(mainSha);
    assert.equal(sameSource.status, 0, sameSource.stderr);
    assert.equal(readFileSync(log, 'utf8'), 'publish --ignore-scripts --access public --provenance --tag latest --registry=https://registry.npmjs.org\n');
  } finally { rmSync(fixture, { recursive: true, force: true }); }
});
