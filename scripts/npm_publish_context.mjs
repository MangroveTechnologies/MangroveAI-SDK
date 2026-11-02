import { execFileSync } from 'node:child_process';
import { lstatSync, realpathSync } from 'node:fs';
import { createRequire } from 'node:module';
import { join } from 'node:path';

export async function verifyNpmPublishContext(packageRoot, expectedSourceSha) {
  const root = execFileSync('git', ['rev-parse', '--show-toplevel'], { cwd: packageRoot, encoding: 'utf8' }).trim();
  if (!lstatSync(join(root, '.git')).isDirectory()) throw new Error('Directory publication requires a normal .git directory so npm can derive gitHead');
  const head = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: packageRoot, encoding: 'utf8' }).trim();
  if (!/^[0-9a-f]{40}$/.test(expectedSourceSha ?? '') || head !== expectedSourceSha) throw new Error('Publication checkout differs from selected source');
  const npmCli = realpathSync(execFileSync('which', ['npm'], { encoding: 'utf8' }).trim());
  const npmRequire = createRequire(npmCli);
  const PackageJson = npmRequire('@npmcli/package-json');
  const { content } = await (await PackageJson.fix(packageRoot)).prepare();
  if (content.gitHead !== expectedSourceSha) throw new Error('Official npm manifest preparation did not derive the selected gitHead');
  return { name: content.name, version: content.version, gitHead: content.gitHead };
}
