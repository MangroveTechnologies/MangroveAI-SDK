import assert from 'node:assert/strict';
import test from 'node:test';
import { createHash } from 'node:crypto';
import { completeTypeScriptRelease, HISTORICAL_MARKETS_VERSIONS, MIGRATION_NOTICE } from '../../../scripts/complete_typescript_release.mjs';

const manifest = { name: '@mangrove-ai/sdk', version: '1.0.0', repository: { url: 'https://github.com/MangroveTechnologies/MangroveAI-SDK.git', directory: 'packages/typescript' } };
const lock = { name: manifest.name, version: manifest.version, packages: { '': { name: manifest.name, version: manifest.version } } };
const markets = { name: '@mangrove-ai/markets', version: '0.4.0', repository: { url: 'https://github.com/MangroveTechnologies/MangroveMarkets.git' } };
const bytes = Buffer.from('fixture artifact');
const integrity = `sha512-${createHash('sha512').update(bytes).digest('base64')}`;
const sha256 = createHash('sha256').update(bytes).digest('hex');
const sourceSha = 'a'.repeat(40);
const published = { gitHead: sourceSha, name: manifest.name, version: manifest.version, repository: manifest.repository, dist: { integrity, tarball: 'https://registry.npmjs.org/@mangrove-ai/sdk/-/sdk-1.0.0.tgz' } };
const fixture = (body = published) => ({ manifest, lock, version: manifest.version, artifact: { sourceSha, integrity, sha256 }, finalize: async () => ({ tag: 'typescript-v1.0.0' }), dryRun: false, publishedSuccessfully: true,
  request: async url => url.endsWith('.tgz') ? new Response(bytes) : ({ status: 200, json: async () => url.includes('%2Fmarkets/') ? markets : body }),
});

test('migration notices target only the three exact historical Markets versions after both registry checks', async () => {
  const order = [];
  const args = fixture();
  const request = args.request;
  args.request = async url => { order.push(url); return request(url); };
  args.finalize = async () => { order.push('verified-tag-release-assets'); };
  args.deprecate = async (target, message) => { order.push(target); assert.equal(message, MIGRATION_NOTICE); };
  const result = await completeTypeScriptRelease(args);
  assert.deepEqual(HISTORICAL_MARKETS_VERSIONS, ['0.1.2', '0.2.0', '0.3.0']);
  assert.deepEqual(order.slice(4), ['@mangrove-ai/sdk@0.1.2', '@mangrove-ai/sdk@0.2.0', '@mangrove-ai/sdk@0.3.0']);
  assert.equal(order[3], 'verified-tag-release-assets');
  assert.match(order[0], /%2Fmarkets\/0\.4\.0$/); assert.match(order[1], /%2Fsdk\/1\.0\.0$/);
  assert.deepEqual(result.deprecated, order.slice(4));
});
test('dry runs and failed publication perform no registry or deprecation calls', async () => {
  for (const controls of [{ dryRun: true }, { publishedSuccessfully: false }]) {
    const noCall = async () => { assert.fail('No external operation is allowed'); };
    const result = await completeTypeScriptRelease({ ...fixture(), ...controls, request: noCall, deprecate: noCall });
    assert.equal(result.skipped, true); assert.deepEqual(result.deprecated, []);
  }
});
test('missing AI registry publication cannot trigger migration notices', async () => {
  const args = fixture(); args.request = async url => ({ status: url.includes('%2Fmarkets/') ? 200 : 404, json: async () => markets });
  args.deprecate = async () => assert.fail('No notice before verified publication');
  await assert.rejects(completeTypeScriptRelease(args), /not verified/);
});
test('wrong published package/version/repository/integrity cannot trigger migration notices', async () => {
  for (const metadata of [{ ...published, name: '@mangrove-ai/client' }, { ...published, version: '0.3.0' }, { ...published, repository: { url: 'https://github.com/other/repo' } }, { ...published, dist: { integrity: 'sha512-b3RoZXI=' } }]) {
    await assert.rejects(completeTypeScriptRelease({ ...fixture(metadata), deprecate: async () => assert.fail('No notice for a different artifact') }), /conflicts/);
  }
});
test('the Markets replacement must exist before any migration notice', async () => {
  await assert.rejects(completeTypeScriptRelease({ ...fixture(), request: async () => ({ status: 404 }), deprecate: async () => assert.fail('No notice without replacement') }), /Publish and verify/);
});
test('a failed version-specific notice stops the sequence without expanding its targets', async () => {
  const seen = [];
  await assert.rejects(completeTypeScriptRelease({ ...fixture(), deprecate: async target => { seen.push(target); if (seen.length === 2) throw new Error('fixture failure'); } }), /fixture failure/);
  assert.deepEqual(seen, ['@mangrove-ai/sdk@0.1.2', '@mangrove-ai/sdk@0.2.0']);
});

test('a failed tag or GitHub Release finalization cannot deprecate a version', async () => {
  await assert.rejects(completeTypeScriptRelease({ ...fixture(), finalize: async () => { throw new Error('tag fixture failure'); }, deprecate: async () => assert.fail('No notice after release failure') }), /tag fixture failure/);
});

test('correct npm metadata with tampered tarball stops before tags, releases or deprecations', async () => {
  const args = fixture(); const request = args.request;
  args.request = async (url, options) => {
    assert.equal(options.redirect, 'error'); assert.equal(options.headers.Authorization, undefined); assert.ok(options.signal);
    return url.endsWith('.tgz') ? new Response('tampered bytes') : request(url, options);
  };
  args.finalize = args.deprecate = async () => assert.fail('No external mutation before byte verification');
  await assert.rejects(completeTypeScriptRelease(args), /checksum conflicts/);
});
test('untrusted tarball origins and oversized archives stop before finalization', async () => {
  for (const tarball of ['http://registry.npmjs.org/fixture.tgz', 'https://other.example.test/fixture.tgz', 'https://user:password@registry.npmjs.org/fixture.tgz']) {
    await assert.rejects(completeTypeScriptRelease({ ...fixture({ ...published, dist: { ...published.dist, tarball } }), finalize: async () => assert.fail('No untrusted archive') }), /tarball URL/);
  }
  const args = fixture(); const request = args.request;
  args.request = async url => url.endsWith('.tgz') ? new Response(bytes, { headers: { 'Content-Length': String(17 * 1024 * 1024) } }) : request(url);
  args.finalize = async () => assert.fail('No oversized archive');
  await assert.rejects(completeTypeScriptRelease(args), /size limit/);
});
