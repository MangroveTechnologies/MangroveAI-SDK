import { createHash } from 'node:crypto';

const REPOSITORY = 'MangroveTechnologies/MangroveAI-SDK';
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const jsonBytes = value => Buffer.from(JSON.stringify(value, null, 2) + '\n');
const requireStatus = (response, expected, message) => { if (!expected.includes(response.status)) throw new Error(`${message}: HTTP${response.status}`); };

export async function ensureGitHubTypeScriptRelease({ artifact, archive, api, downloadAsset }) {
  if (artifact.name !== '@mangrove-ai/sdk' || !/^[0-9a-f]{40}$/.test(artifact.sourceSha) || digest(archive) !== artifact.sha256) throw new Error('GitHub release artifact/source identity is invalid');
  const tag = `typescript-v${artifact.version}`;
  const provenance = { schema_version: 1, package: artifact.name, version: artifact.version, source_sha: artifact.sourceSha, repository: REPOSITORY, npm_integrity: artifact.integrity, sha256: artifact.sha256, filename: artifact.filename, tag };
  const body = `MangroveAI TypeScript SDK ${artifact.version}\n\nSource: https://github.com/${REPOSITORY}/commit/${artifact.sourceSha}\nPackage: ${artifact.name}@${artifact.version}\nSHA-256: ${artifact.sha256}\nIntegrity: ${artifact.integrity}\n\nHistorical @mangrove-ai/sdk0.x versions are Markets. Markets moved to @mangrove-ai/markets0.4.0.\n`.replace('sdk0.x', 'sdk 0.x').replace('markets0.4.0', 'markets 0.4.0');
  const refPath = `/repos/${REPOSITORY}/git/ref/tags/${encodeURIComponent(tag)}`;
  const checkTag = async () => {
    const ref = await api('GET', refPath); requireStatus(ref, [200], 'Read annotated tag');
    if (ref.data.object?.type !== 'tag') throw new Error('Release tag must be annotated');
    const annotated = await api('GET', `/repos/${REPOSITORY}/git/tags/${ref.data.object.sha}`); requireStatus(annotated, [200], 'Read tag annotation');
    if (annotated.data.tag !== tag || annotated.data.object?.type !== 'commit' || annotated.data.object.sha !== artifact.sourceSha || annotated.data.message !== body) throw new Error('Existing annotated tag conflicts with the exact source/checksum');
  };
  let ref = await api('GET', refPath);
  if (ref.status === 404) {
    const annotated = await api('POST', `/repos/${REPOSITORY}/git/tags`, { tag, message: body, object: artifact.sourceSha, type: 'commit' }); requireStatus(annotated, [201], 'Create tag annotation');
    const created = await api('POST', `/repos/${REPOSITORY}/git/refs`, { ref: `refs/tags/${tag}`, sha: annotated.data.sha }); requireStatus(created, [201, 422], 'Create tag ref');
  } else requireStatus(ref, [200], 'Read release tag');
  await checkTag();
  const releasePath = `/repos/${REPOSITORY}/releases/tags/${encodeURIComponent(tag)}`;
  let release = await api('GET', releasePath);
  if (release.status === 404) {
    const created = await api('POST', `/repos/${REPOSITORY}/releases`, { tag_name: tag, target_commitish: artifact.sourceSha, name: `${artifact.name}@${artifact.version}`, body, draft: false, prerelease: artifact.version.includes('-'), make_latest: 'false' }); requireStatus(created, [201, 422], 'Create GitHub Release');
    release = await api('GET', releasePath);
  }
  requireStatus(release, [200], 'Read GitHub Release');
  const checkRelease = data => {
    if (data.tag_name !== tag || data.name !== `${artifact.name}@${artifact.version}` || data.body !== body || data.draft || data.prerelease !== artifact.version.includes('-')) throw new Error('Existing GitHub Release conflicts with source/checksum metadata');
  };
  checkRelease(release.data);
  const files = new Map([[artifact.filename, archive], [`${artifact.filename}.sha256`, Buffer.from(`${artifact.sha256}  ${artifact.filename}\n`)], ['release-provenance.json', jsonBytes(provenance)]]);
  if ((release.data.assets ?? []).some(asset => !files.has(asset.name))) throw new Error('Unexpected release asset conflicts with reviewed output');
  const verifyAsset = async (asset, name, bytes) => {
    if (asset.size !== bytes.length) throw new Error(`Existing release asset size conflicts: ${name}`);
    if (asset.digest !== `sha256:${digest(bytes)}`) throw new Error(`Existing release asset digest conflicts: ${name}`);
    const actual = digest(await downloadAsset(tag, name));
    if (actual !== digest(bytes)) throw new Error(`Existing release asset checksum conflicts: ${name}`);
  };
  for (const [name, bytes] of files) {
    const matches = (release.data.assets ?? []).filter(asset => asset.name === name);
    if (matches.length > 1) throw new Error('Duplicate release assets conflict');
    if (matches[0]) await verifyAsset(matches[0], name, bytes);
    else {
      const uploaded = await api('UPLOAD', `/repos/${REPOSITORY}/releases/${release.data.id}/assets?name=${encodeURIComponent(name)}`, bytes); requireStatus(uploaded, [201], 'Upload release asset');
      await verifyAsset(uploaded.data, name, bytes);
    }
  }
  release = await api('GET', releasePath); requireStatus(release, [200], 'Read completed release'); checkRelease(release.data);
  if ((release.data.assets ?? []).length !== files.size) throw new Error('Release asset set differs from the reviewed output');
  for (const [name, bytes] of files) {
    const asset = release.data.assets.find(item => item.name === name); if (!asset) throw new Error('Missing release asset'); await verifyAsset(asset, name, bytes);
  }
  await checkTag();
  return provenance;
}

export function githubReleaseTransport(token, request = globalThis.fetch) {
  if (!token) throw new Error('GITHUB_TOKEN is required for native tag/release finalization');
  const deadline = AbortSignal.timeout(120000);
  return {
    api: async (method, path, body) => {
      const upload = method === 'UPLOAD';
      const url = `https://${upload ? 'uploads.github.com' : 'api.github.com'}${path}`;
      const response = await request(url, { method: upload ? 'POST' : method, redirect: 'error', signal: deadline, headers: { Accept: 'application/vnd.github+json', Authorization: `Bearer ${token}`, 'X-GitHub-Api-Version': '2026-03-10', ...(body ? { 'Content-Type': upload ? 'application/octet-stream' : 'application/json' } : {}) }, ...(body ? { body: upload ? body : JSON.stringify(body) } : {}) });
      return { status: response.status, data: response.status === 204 ? {} : await response.json() };
    },
    downloadAsset: async (tag, name) => {
      const response = await request(`https://github.com/${REPOSITORY}/releases/download/${encodeURIComponent(tag)}/${encodeURIComponent(name)}`, { redirect: 'follow', signal: deadline });
      if (!response.ok) throw new Error('Release asset readback failed');
      if (Number(response.headers.get('content-length')) > 16 * 1024 * 1024) throw new Error('Release asset exceeds readback limit');
      if (!response.body) throw new Error('Release asset body unavailable');
      const reader = response.body.getReader(); const chunks = []; let size = 0;
      while (true) { const { done, value } = await reader.read(); if (done) break; size += value.byteLength; if (size > 16 * 1024 * 1024) { await reader.cancel(); throw new Error('Release asset exceeds readback limit'); } chunks.push(value); }
      return Buffer.concat(chunks);
    },
  };
}
