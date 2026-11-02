import { readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import childProcess from 'node:child_process';
import { syncBuiltinESMExports } from 'node:module';

const manifest = JSON.parse(readFileSync('packages/typescript/package.json'));
const artifact = JSON.parse(readFileSync('artifact.json'));
const settings = JSON.parse(readFileSync('scenario.json'));
const archive = readFileSync(artifact.filename);
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const tag = `typescript-v${artifact.version}`;
const body = `MangroveAI TypeScript SDK ${artifact.version}\n\nSource: https://github.com/MangroveTechnologies/MangroveAI-SDK/commit/${artifact.sourceSha}\nPackage: ${artifact.name}@${artifact.version}\nSHA-256: ${artifact.sha256}\nIntegrity: ${artifact.integrity}\n\nHistorical @mangrove-ai/sdk 0.x versions are Markets. Markets moved to @mangrove-ai/markets 0.4.0.\n`;
const provenance = { schema_version: 1, package: artifact.name, version: artifact.version, source_sha: artifact.sourceSha, repository: 'MangroveTechnologies/MangroveAI-SDK', npm_integrity: artifact.integrity, sha256: artifact.sha256, filename: artifact.filename, tag };
const assets = new Map([[artifact.filename, archive], [`${artifact.filename}.sha256`, Buffer.from(`${artifact.sha256}  ${artifact.filename}\n`)], ['release-provenance.json', Buffer.from(JSON.stringify(provenance, null, 2) + '\n')]]);
const timers = [];
const observed = { clock: 0, metadataReads: 0, archiveReads: 0, requests: [], commands: [], notices: { ...settings.notices } };
let annotationReads = 0;
const advance = ms => {
  observed.clock += ms;
  for (const timer of timers) if (timer.at <= observed.clock && !timer.controller.signal.aborted) timer.controller.abort(new DOMException('fixture timeout', 'TimeoutError'));
};
Object.defineProperty(performance, 'now', { value: () => observed.clock });
Object.defineProperty(AbortSignal, 'timeout', { value: ms => {
  const controller = new AbortController();
  timers.push({ at: observed.clock + ms, controller });
  return controller.signal;
} });
globalThis.setTimeout = (done, ms) => { advance(ms); queueMicrotask(done); return 0; };
childProcess.execFileSync = (command, args) => {
  observed.commands.push({ command, args });
  if (annotationReads !== 2) throw new Error('Notice operation preceded full tag/release/asset verification');
  if (command === 'npm' && args[0] === 'view' && args[2] === 'deprecated') {
    if (settings.noticeError) throw new Error('fixture notice authentication/network failure');
    return (observed.notices[args[1]] ?? '') + '\n';
  }
  if (command === 'npm' && args[0] === 'deprecate' && ['0.1.2', '0.2.0', '0.3.0'].some(version => args[1] === `@mangrove-ai/sdk@${version}`)) {
    if (observed.notices[args[1]] === args[2]) throw new Error('fixture npm422: matching notice must not be rewritten');
    observed.notices[args[1]] = args[2];
    return Buffer.alloc(0);
  }
  throw new Error('Unexpected child command blocked');
};
for (const method of ['exec', 'execSync', 'execFile', 'spawn', 'spawnSync', 'fork']) childProcess[method] = () => { throw new Error('External child process blocked'); };
syncBuiltinESMExports();
globalThis.fetch = async (input, options = {}) => {
  const url = new URL(input);
  const method = options.method ?? 'GET';
  if (url.hostname === 'api.github.com' && settings.githubDelay && !observed.requests.some(call => call.host === 'api.github.com')) advance(settings.githubDelay);
  observed.requests.push({ host: url.hostname, path: url.pathname, method, at: observed.clock, aborted: options.signal?.aborted ?? false });
  if (options.signal?.aborted) throw options.signal.reason;
  if (method !== 'GET') throw new Error('Unexpected HTTP write blocked');
  if (url.hostname === 'registry.npmjs.org') {
    if (url.pathname.includes('%2Fmarkets/')) return Response.json({ name: '@mangrove-ai/markets', version: '0.4.0', repository: 'https://github.com/MangroveTechnologies/MangroveMarkets' });
    if (url.pathname.endsWith('.tgz')) {
      if (settings.archiveNetworkError) throw new Error('fixture archive network failure');
      if (settings.archiveStatus) return new Response('', { status: settings.archiveStatus });
      if (++observed.archiveReads <= (settings.archive404s ?? 0)) return new Response('', { status: 404 });
      return new Response(settings.archiveCorrupt ? Buffer.from('tampered archive') : archive);
    }
    if (url.pathname.endsWith(`%2Fsdk/${artifact.version}`)) {
      observed.metadataReads++;
      if (settings.registryNetworkError) throw new Error('fixture registry network failure');
      if (settings.registryStatus) return new Response('', { status: settings.registryStatus });
      if (observed.metadataReads <= settings.metadata404s) return new Response('', { status: 404 });
      return Response.json({ ...manifest, gitHead: settings.metadataSource ?? artifact.sourceSha, dist: { integrity: settings.metadataIntegrity ?? artifact.integrity, tarball: `https://registry.npmjs.org/@mangrove-ai/sdk/-/sdk-${artifact.version}.tgz` } });
    }
  }
  if (url.hostname === 'api.github.com') {
    if (settings.githubStatus) return Response.json({}, { status: settings.githubStatus });
    if (settings.githubNetworkError) throw new Error('fixture GitHub network failure');
    if (url.pathname.includes('/git/ref/tags/')) return Response.json({ object: { type: settings.tagType ?? 'tag', sha: 'b'.repeat(40) } });
    if (url.pathname.includes('/git/tags/')) { annotationReads++; return Response.json({ tag, message: body, object: { type: 'commit', sha: settings.tagSource ?? artifact.sourceSha } }); }
    if (url.pathname.includes('/releases/tags/')) return Response.json({ id: 1, tag_name: tag, name: `${manifest.name}@${manifest.version}`, body: settings.releaseBody ?? body, draft: false, prerelease: false, assets: [...assets].map(([name, bytes]) => ({ name, size: bytes.length, digest: `sha256:${settings.assetDigestConflict && name === artifact.filename ? 'f'.repeat(64) : sha(bytes)}` })) });
  }
  if (url.hostname === 'github.com' && url.pathname.includes('/releases/download/')) {
    const bytes = assets.get(decodeURIComponent(url.pathname.split('/').at(-1)));
    if (bytes) return new Response(settings.assetBytesConflict && url.pathname.endsWith(artifact.filename) ? Buffer.from('wrong asset bytes') : bytes);
  }
  throw new Error('Unexpected external request blocked');
};
process.on('exit', () => writeFileSync('observed.json', JSON.stringify(observed, null, 2) + '\n'));
