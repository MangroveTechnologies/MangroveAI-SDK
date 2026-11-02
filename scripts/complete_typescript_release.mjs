import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { registryOptions, validateReleaseIdentity, verifyPublishedAiArtifact, verifyPublishedMarkets } from './check_typescript_release.mjs';
import { ensureGitHubTypeScriptRelease, githubReleaseTransport } from './github_typescript_release.mjs';

export const HISTORICAL_MARKETS_VERSIONS = Object.freeze(['0.1.2', '0.2.0', '0.3.0']);
export const MIGRATION_NOTICE = 'This version is the historical MangroveMarkets SDK. Migrate to @mangrove-ai/markets@0.4.0. @mangrove-ai/sdk versions 1.x and later are the separate MangroveAI SDK with a different API.';

export async function completeTypeScriptRelease({ manifest, lock, version, artifact, dryRun = true, publishedSuccessfully = false, request = globalThis.fetch, finalize, deprecate }) {
  if (dryRun || !publishedSuccessfully) return { skipped: true, reason: dryRun ? 'dry run' : 'publication did not succeed', deprecated: [] };
  validateReleaseIdentity({ manifest, lock, version });
  await verifyPublishedMarkets(request);
  const response = await request(`https://registry.npmjs.org/${encodeURIComponent(manifest.name)}/${manifest.version}`, registryOptions());
  if (response.status !== 200) throw new Error('AI publication is not verified; no historical version was changed');
  await verifyPublishedAiArtifact(await response.json(), { manifest, artifact, request });
  if (typeof finalize !== 'function') throw new Error('Verified annotated tag, GitHub Release and assets are required before migration notices');
  const githubRelease = await finalize();
  const deprecated = [];
  for (const historical of HISTORICAL_MARKETS_VERSIONS) {
    const target = `@mangrove-ai/sdk@${historical}`;
    await deprecate(target, MIGRATION_NOTICE);
    deprecated.push(target);
  }
  return { skipped: false, name: manifest.name, version: manifest.version, integrity: artifact.integrity, githubRelease, deprecated };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const dryRun = process.env.DRY_RUN !== 'false';
  const publishedSuccessfully = process.env.PUBLISH_SUCCEEDED === 'true';
  if (dryRun || !publishedSuccessfully) {
    console.log('Migration notices skipped: dry run or publication did not succeed');
  } else {
    const manifest = JSON.parse(readFileSync('packages/typescript/package.json', 'utf8'));
    const lock = JSON.parse(readFileSync('packages/typescript/package-lock.json', 'utf8'));
    const artifact = JSON.parse(readFileSync(process.env.RELEASE_ARTIFACT, 'utf8'));
    const archive = readFileSync(join(dirname(process.env.RELEASE_ARTIFACT), artifact.filename));
    const transport = githubReleaseTransport(process.env.GITHUB_TOKEN);
    const result = await completeTypeScriptRelease({ manifest, lock, version: process.env.EXPECTED_VERSION, artifact, dryRun, publishedSuccessfully,
      finalize: () => ensureGitHubTypeScriptRelease({ artifact, archive, ...transport }),
      deprecate: (target, message) => execFileSync('npm', ['deprecate', target, message, '--registry=https://registry.npmjs.org'], { cwd: 'packages/typescript', stdio: 'inherit' }),
    });
    console.log(JSON.stringify(result));
  }
}
