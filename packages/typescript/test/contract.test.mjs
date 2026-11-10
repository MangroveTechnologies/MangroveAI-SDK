import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const root = resolve(packageRoot, '../..');

test('reviewed input changes fail the generation gate before stale types can ship', () => {
  const parent = join(packageRoot, '.contract-tests');
  mkdirSync(parent, { recursive: true });
  const scratch = mkdtempSync(join(parent, 'drift-'));
  try {
    for (const path of ['contracts/mangroveai', 'scripts/generate_typescript_contract.py', 'packages/typescript/src/contract.generated.ts', 'src/mangrove_ai/_services']) {
      mkdirSync(dirname(join(scratch, path)), { recursive: true });
      cpSync(join(root, path), join(scratch, path), { recursive: true });
    }
    const run = () => spawnSync('python3', ['scripts/generate_typescript_contract.py', '--check'], { cwd: scratch, encoding: 'utf8' });
    const baseline = run();
    assert.equal(baseline.status, 0, baseline.stdout + baseline.stderr);
    const source = join(scratch, 'contracts/mangroveai/openapi.json');
    const schema = JSON.parse(readFileSync(source, 'utf8'));
    schema.definitions['api1.UserMetrics'].properties.messages_count.type = 'string';
    writeFileSync(source, JSON.stringify(schema));
    const provenancePath = join(scratch, 'contracts/mangroveai/provenance.json');
    const provenance = JSON.parse(readFileSync(provenancePath, 'utf8'));
    provenance.contracts.find(entry => entry.path === 'openapi.json').sha256 = createHash('sha256').update(readFileSync(source)).digest('hex');
    writeFileSync(provenancePath, JSON.stringify(provenance));
    const changed = run();
    assert.notEqual(changed.status, 0);
    assert.match(changed.stderr + changed.stdout, /Contract drift/);
  } finally { rmSync(scratch, { recursive: true, force: true }); }
});
