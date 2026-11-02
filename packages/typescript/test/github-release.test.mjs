import assert from 'node:assert/strict';
import test from 'node:test';
import { createHash } from 'node:crypto';
import { ensureGitHubTypeScriptRelease } from '../../../scripts/github_typescript_release.mjs';

const archive = Buffer.from('fixture archive');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const artifact = { name: '@mangrove-ai/sdk', version: '1.0.0', sourceSha: 'a'.repeat(40), filename: 'mangrove-ai-sdk-1.0.0.tgz', integrity: 'sha512-Zml4dHVyZQ==', sha256: sha(archive) };
function fixture() {
  const state = { ref: null, annotation: null, release: null, assets: new Map(), writes: [], failUpload: null };
  const clone = data => data === null ? null : JSON.parse(JSON.stringify(data));
  const api = async (method, path, body) => {
    if (path.includes('/git/ref/tags/')) return { status: state.ref ? 200 : 404, data: clone(state.ref) };
    if (path.endsWith('/git/tags') && method === 'POST') { state.writes.push('annotation'); state.annotation = { tag: body.tag, message: body.message, object: { type: body.type, sha: body.object } }; return { status: 201, data: { sha: 'b'.repeat(40) } }; }
    if (path.endsWith('/git/refs')) { state.writes.push('ref'); state.ref = { object: { type: 'tag', sha: body.sha } }; return { status: 201, data: clone(state.ref) }; }
    if (path.includes('/git/tags/')) return { status: 200, data: clone(state.annotation) };
    if (path.includes('/releases/tags/')) return { status: state.release ? 200 : 404, data: state.release ? { ...clone(state.release), assets: [...state.assets.values()].map(item => clone(item.metadata)) } : null };
    if (path.endsWith('/releases') && method === 'POST') { state.writes.push('release'); state.release = { ...body, id: 1 }; return { status: 201, data: clone(state.release) }; }
    if (method === 'UPLOAD') {
      const name = new URL('https://uploads.github.com' + path).searchParams.get('name');
      if (state.failUpload === name) { state.failUpload = null; return { status: 500, data: {} }; }
      state.writes.push(name); const metadata = { name, size: body.length, digest: `sha256:${sha(body)}` }; state.assets.set(name, { metadata, bytes: Buffer.from(body) }); return { status: 201, data: clone(metadata) };
    }
    assert.fail(`Unexpected fixture operation: ${method} ${path}`);
  };
  return { state, run: () => ensureGitHubTypeScriptRelease({ artifact, archive, api, downloadAsset: async (_tag, name) => state.assets.get(name).bytes }) };
}

test('native finalization creates an annotated source-bound tag and published release with verified assets', async () => {
  const f = fixture(); const receipt = await f.run();
  assert.equal(receipt.tag, 'typescript-v1.0.0'); assert.equal(f.state.annotation.object.sha, artifact.sourceSha);
  assert.equal(f.state.annotation.object.type, 'commit'); assert.equal(f.state.release.draft, false);
  assert.match(f.state.release.body, new RegExp(artifact.sha256)); assert.match(f.state.release.body, new RegExp(artifact.sourceSha));
  assert.equal(f.state.assets.size, 3);
});
test('an exact retry performs no tag/release/asset overwrite', async () => {
  const f = fixture(); await f.run(); const writes = [...f.state.writes]; await f.run(); assert.deepEqual(f.state.writes, writes);
});
test('a partial asset failure resumes only the missing outputs without republishing', async () => {
  const f = fixture(); f.state.failUpload = `${artifact.filename}.sha256`;
  await assert.rejects(f.run(), /Upload release asset/); assert.equal(f.state.assets.size, 1);
  await f.run(); assert.equal(f.state.assets.size, 3); assert.equal(f.state.writes.filter(v => v === 'annotation').length, 1); assert.equal(f.state.writes.filter(v => v === artifact.filename).length, 1);
});
test('lightweight tags and annotated tags pointing at a different commit are rejected', async () => {
  for (const type of ['commit', 'tag']) {
    const f = fixture(); f.state.ref = { object: { type, sha: 'b'.repeat(40) } }; f.state.annotation = { tag: 'typescript-v1.0.0', message: '', object: { type: 'commit', sha: 'c'.repeat(40) } };
    await assert.rejects(f.run(), /annotated|conflicts/); assert.deepEqual(f.state.writes, []);
  }
});
test('an existing draft, wrong body or wrong tag release is never silently adopted', async () => {
  for (const change of [{ draft: true }, { body: 'different source' }, { tag_name: 'v2.1.0' }]) {
    const f = fixture(); await f.run(); Object.assign(f.state.release, change); const writes = [...f.state.writes]; await assert.rejects(f.run(), /conflicts/); assert.deepEqual(f.state.writes, writes);
  }
});
test('asset digest and actual downloaded bytes must both match without clobbering', async () => {
  for (const changeBytes of [false, true]) {
    const f = fixture(); await f.run(); const asset = f.state.assets.get(artifact.filename);
    if (changeBytes) asset.bytes = Buffer.from('bad bytes'); else asset.metadata.digest = 'sha256:' + 'f'.repeat(64);
    const writes = [...f.state.writes]; await assert.rejects(f.run(), /conflicts/); assert.deepEqual(f.state.writes, writes);
  }
});
test('unexpected release assets stop an immutable release rather than being deleted', async () => {
  const f = fixture(); await f.run(); f.state.assets.set('unexpected', { metadata: { name: 'unexpected' }, bytes: Buffer.from('x') }); const writes = [...f.state.writes]; await assert.rejects(f.run(), /Unexpected/); assert.deepEqual(f.state.writes, writes);
});

test('mutable target_commitish main is accepted only through the correct annotated tag', async () => {
  const f = fixture(); await f.run(); f.state.release.target_commitish = 'main';
  await f.run(); f.state.annotation.object.sha = 'd'.repeat(40);
  const writes = [...f.state.writes]; await assert.rejects(f.run(), /annotated tag conflicts/); assert.deepEqual(f.state.writes, writes);
});
