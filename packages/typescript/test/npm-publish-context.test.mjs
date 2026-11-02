import assert from 'node:assert/strict';
import test from 'node:test';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { verifyNpmPublishContext } from '../../../scripts/npm_publish_context.mjs';

test('official npm preparation binds normal branch/detached checkout and rejects a linked worktree', async () => {
  const fixture = mkdtempSync(join(process.cwd(), '.npm-publish-fixture-'));
  const repository = join(fixture, 'repository'); mkdirSync(repository);
  const git = (...args) => execFileSync('git', args, { cwd: repository, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  try {
    git('init', '--initial-branch=fixture');
    writeFileSync(join(repository, 'package.json'), JSON.stringify({ name: '@mangrove-ai/sdk', version: '1.0.0', description: 'fixture package' }));
    git('add', 'package.json');
    git('-c', 'user.name=fixture', '-c', 'user.email=fixture@example.test', 'commit', '-m', 'fixture source');
    const sha = git('rev-parse', 'HEAD');
    assert.equal((await verifyNpmPublishContext(repository, sha)).gitHead, sha);
    git('checkout', '--detach', sha);
    assert.equal((await verifyNpmPublishContext(repository, sha)).gitHead, sha);
    await assert.rejects(verifyNpmPublishContext(repository, 'b'.repeat(40)), /differs/);
    const worktree = join(fixture, 'linked'); git('worktree', 'add', '--detach', worktree, sha);
    await assert.rejects(verifyNpmPublishContext(worktree, sha), /normal \.git/);
    git('worktree', 'remove', worktree);
  } finally { rmSync(fixture, { recursive: true, force: true }); }
});
