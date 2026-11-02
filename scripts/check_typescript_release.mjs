import { appendFileSync, readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const AI_PACKAGE = '@mangrove-ai/sdk';
const MARKETS_PACKAGE = '@mangrove-ai/markets';
const MARKETS_VERSION = '0.4.0';
const AI_REPOSITORY = 'https://github.com/MangroveTechnologies/MangroveAI-SDK';
const MARKETS_REPOSITORY = 'https://github.com/MangroveTechnologies/MangroveMarkets';

export const repositoryUrl = (repository) => (typeof repository === 'string' ? repository : repository?.url ?? '')
  .replace(/^git\+/, '').replace(/\.git$/, '').replace(/\/$/, '');

export function validateReleaseIdentity({ manifest, lock, version }) {
  if (manifest.name !== AI_PACKAGE) throw new Error('This repository releases only @mangrove-ai/sdk');
  const parsed = /^(\d+)\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/.exec(manifest.version ?? '');
  if (!parsed || Number(parsed[1]) < 1) throw new Error('@mangrove-ai/sdk versions below 1.0.0 are historical Markets releases');
  if (manifest.version !== version) throw new Error('Input version does not match reviewed package.json');
  if (repositoryUrl(manifest.repository) !== AI_REPOSITORY || manifest.repository?.directory !== 'packages/typescript') {
    throw new Error('Package repository does not identify the MangroveAI TypeScript SDK');
  }
  if (lock.name !== manifest.name || lock.version !== manifest.version || lock.packages?.['']?.name !== manifest.name || lock.packages?.['']?.version !== manifest.version) {
    throw new Error('package-lock.json root identity does not match package.json');
  }
}

export const registryOptions = () => ({ headers: { Accept: 'application/json' }, redirect: 'error', signal: AbortSignal.timeout(10000) });

export async function verifyPublishedMarkets(request = globalThis.fetch) {
  const markets = await request(`https://registry.npmjs.org/${encodeURIComponent(MARKETS_PACKAGE)}/${MARKETS_VERSION}`, registryOptions());
  if (markets.status !== 200) throw new Error('Publish and verify @mangrove-ai/markets 0.4.0 before the MangroveAI SDK');
  const metadata = await markets.json();
  if (metadata?.name !== MARKETS_PACKAGE || metadata.version !== MARKETS_VERSION || repositoryUrl(metadata.repository) !== MARKETS_REPOSITORY) {
    throw new Error('Markets registry metadata does not identify the reviewed Markets package');
  }
  return metadata;
}

export function verifyPublishedAi(metadata, { manifest, sourceSha, expectedIntegrity }) {
  if (!/^[0-9a-f]{40}$/.test(sourceSha ?? '') || !/^sha512-[A-Za-z0-9+/]+=*$/.test(expectedIntegrity ?? '')) {
    throw new Error('Existing publication requires the exact reviewed source and local artifact integrity');
  }
  if (metadata?.name !== manifest.name || metadata.version !== manifest.version || repositoryUrl(metadata.repository) !== repositoryUrl(manifest.repository) || metadata.gitHead !== sourceSha || metadata.dist?.integrity !== expectedIntegrity) {
    throw new Error('Published AI registry identity, gitHead or integrity conflicts with the reviewed artifact');
  }
}

export async function verifyPublishedAiArtifact(metadata, { manifest, artifact, request = globalThis.fetch }) {
  verifyPublishedAi(metadata, { manifest, sourceSha: artifact?.sourceSha, expectedIntegrity: artifact?.integrity });
  const url = new URL(metadata.dist?.tarball ?? '');
  if (url.protocol !== 'https:' || url.hostname !== 'registry.npmjs.org' || url.username || url.password || url.search || url.hash || url.port) throw new Error('AI tarball URL must be the public HTTPS npm registry without credentials or redirects');
  const response = await request(url.href, { ...registryOptions(), headers: { Accept: 'application/octet-stream' } });
  if (!response.ok || !response.body) throw new Error('Published npm archive download failed');
  const maximum = 16 * 1024 * 1024;
  if (Number(response.headers.get('content-length')) > maximum) throw new Error('Published npm archive exceeds size limit');
  const reader = response.body.getReader(); const chunks = []; let size = 0;
  while (true) {
    const { done, value } = await reader.read(); if (done) break;
    size += value.byteLength; if (size > maximum) { await reader.cancel(); throw new Error('Published npm archive exceeds size limit'); } chunks.push(value);
  }
  const bytes = Buffer.concat(chunks);
  if (`sha512-${createHash('sha512').update(bytes).digest('base64')}` !== artifact.integrity || createHash('sha256').update(bytes).digest('hex') !== artifact.sha256) throw new Error('Downloaded npm archive checksum conflicts with the reviewed artifact');
  return bytes;
}

export async function checkTypeScriptRelease({ manifest, lock, version, artifact, currentMainSha, requireMarketsRelease = false, request = globalThis.fetch }) {
  validateReleaseIdentity({ manifest, lock, version });
  const response = await request(`https://registry.npmjs.org/${encodeURIComponent(manifest.name)}/${manifest.version}`, registryOptions());
  let publishRequired;
  if (response.status === 404) {
    if (requireMarketsRelease && (!artifact?.sourceSha || artifact.sourceSha !== currentMainSha)) throw new Error('New publication requires the fresh current main source; old ancestors are recovery-only');
    publishRequired = true;
  }
  else if (response.status === 200) {
    await verifyPublishedAiArtifact(await response.json(), { manifest, artifact, request });
    publishRequired = false;
  } else throw new Error(`Registry preflight failed: ${response.status}`);
  if (requireMarketsRelease) await verifyPublishedMarkets(request);
  return { name: manifest.name, version: manifest.version, marketsReleaseRequired: requireMarketsRelease, publishRequired };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const manifest = JSON.parse(readFileSync('packages/typescript/package.json', 'utf8'));
  const lock = JSON.parse(readFileSync('packages/typescript/package-lock.json', 'utf8'));
  const artifact = JSON.parse(readFileSync(process.env.RELEASE_ARTIFACT, 'utf8'));
  const currentMainSha = execFileSync('git', ['ls-remote', 'origin', 'refs/heads/main'], { encoding: 'utf8' }).trim().split(/\s+/)[0];
  const result = await checkTypeScriptRelease({ manifest, lock, currentMainSha, version: process.env.EXPECTED_VERSION, artifact, requireMarketsRelease: process.env.REQUIRE_MARKETS_RELEASE === 'true' });
  if (process.env.GITHUB_OUTPUT) appendFileSync(process.env.GITHUB_OUTPUT, `publish_required=${result.publishRequired}\n`);
  console.log(JSON.stringify(result));
}
