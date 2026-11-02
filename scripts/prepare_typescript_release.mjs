import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { appendFileSync, chmodSync, existsSync, mkdirSync, readFileSync, unlinkSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { validateReleaseIdentity } from './check_typescript_release.mjs';
import { verifyNpmPublishContext } from './npm_publish_context.mjs';

const manifest = JSON.parse(readFileSync('packages/typescript/package.json', 'utf8'));
const lock = JSON.parse(readFileSync('packages/typescript/package-lock.json', 'utf8'));
validateReleaseIdentity({ manifest, lock, version: process.env.EXPECTED_VERSION });
const sourceSha = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
if (sourceSha !== process.env.SOURCE_SHA || !/^[0-9a-f]{40}$/.test(sourceSha)) throw new Error('Build source is not the selected reviewed commit');
if (execFileSync('git', ['status', '--porcelain'], { encoding: 'utf8' }).trim()) throw new Error('Release source must be clean');
const npmManifest = await verifyNpmPublishContext(resolve('packages/typescript'), sourceSha);
const directory = process.env.RELEASE_ARTIFACT_DIR;
if (!directory) throw new Error('RELEASE_ARTIFACT_DIR is required');
mkdirSync(directory, { recursive: true });
const packed = JSON.parse(execFileSync('npm', ['pack', '--ignore-scripts', '--json', '--pack-destination', directory], { cwd: 'packages/typescript', encoding: 'utf8' }))[0];
if (packed.name !== manifest.name || packed.version !== manifest.version) throw new Error('Packed package identity differs from source');
const filename = `mangrove-ai-sdk-${manifest.version}.tgz`;
if (packed.filename !== filename) throw new Error('Unexpected archive filename');
const bytes = readFileSync(join(directory, filename));
const integrity = `sha512-${createHash('sha512').update(bytes).digest('base64')}`;
if (integrity !== packed.integrity) throw new Error('Packed archive integrity differs from npm metadata');
const sha256 = createHash('sha256').update(bytes).digest('hex');
const immutableDirectory = join(directory, 'sha256', sha256); mkdirSync(immutableDirectory, { recursive: true });
const immutable = (path, body) => {
  if (existsSync(path)) { if (!readFileSync(path).equals(Buffer.from(body))) throw new Error('Immutable release output conflicts'); }
  else writeFileSync(path, body, { flag: 'wx', mode: 0o400 });
  chmodSync(path, 0o400);
};
immutable(join(immutableDirectory, filename), bytes);
const receipt = { name: manifest.name, version: manifest.version, sourceSha, npmManifestGitHead: npmManifest.gitHead, filename, integrity, sha256 };
const receiptPath = join(immutableDirectory, 'release-artifact.json');
immutable(receiptPath, JSON.stringify(receipt, null, 2) + '\n');
unlinkSync(join(directory, filename));
if (process.env.GITHUB_ENV) appendFileSync(process.env.GITHUB_ENV, `RELEASE_ARTIFACT=${receiptPath}\n`);
console.log(JSON.stringify({ ...receipt, receiptPath }));
