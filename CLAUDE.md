# MangroveAI SDKs: Python and TypeScript

This repository contains clients for the public MangroveAI services in both
languages. Keep their package identities and capabilities distinct:

- Python: PyPI `mangroveai`, import `from mangrove_ai import MangroveAI`, source
  `src/mangrove_ai/`. Python 2.2.0 is published; 2.3.0 is the prepared source candidate.
- TypeScript: npm `@mangrove-ai/sdk` 1.x, import
  `import { MangroveAI } from '@mangrove-ai/sdk'`, source `packages/typescript/`.
  The published version is 1.1.0; 1.2.0 is the prepared source candidate. Use the [guide](packages/typescript/README.md),
  [migration notice](docs/typescript-package-migration.md) and [dated release status](docs/issue-66-release-handoff.md)
  before claiming registry availability.
- MangroveMarkets moves to `@mangrove-ai/markets` 0.4.0 with its existing
  `MangroveClient` export. Published `@mangrove-ai/sdk` 0.1.2, 0.2.0 and 0.3.0
  are historical Markets releases, not the AI SDK. Never overwrite those versions.
- The user's explicit 2026-11-02 naming decision replaces the earlier naming plan.
  `@mangrove-ai/client` was unpublished and must not be published or kept as an alias.
  AI 1.0.0 is a breaking product move, not Markets API compatibility.

TypeScript provides named `users`, `signals`, `strategies`, `strategyWorkflow` and `backtesting`
helpers and a generated generic `request(operation, options)` surface, not
Python method parity. The pinned public classification contains 268 core/Oracle
proxy method/path operations including 10 v2: 264 JSON/no-content, one separate
redirect flow and three streaming/non-JSON operations. Counts describe declarations,
not authenticated live coverage. MCP/OAuth discovery, the separate legacy KB
host, x402 signing and SSE consumption are outside this JSON client.

Do not export private Oracle contracts. Mangrove owns deterministic risk
management based on live market and account conditions; clients preserve its
decisions and audit results rather than inventing their own enforcement. Keep
product-specific credentials and base URLs separate. Python AI expects `/api/v1`,
Python Markets expects an origin, and AI TypeScript accepts an origin or versioned
base; do not encourage one shared `MANGROVE_BASE_URL` across products.

Sibling repos:
- `MangroveAI` — the backend whose HTTP API this SDK wraps. Not to be confused with this SDK.
- `MangroveMarkets/packages/python-sdk` — sibling SDK for the markets API (`mangrovemarkets` on PyPI, `mangrove_markets` import path).
- `mangrove-agent`, `live-strategies` — consumers that `pip install mangroveai`.

See parent [`CLAUDE.md`](../CLAUDE.md) for portfolio-wide rules. See [`mangrove/.claude/rules/git-workflow.md`](../.claude/rules/git-workflow.md) before any work.

## Distribution name ≠ import name (intentional)

```
pip install mangroveai      ← PyPI distribution name (no hyphen)
from mangrove_ai import ... ← import path (with underscore)
```

This is the Pillow/PIL pattern (`pip install Pillow` → `from PIL import Image`). Distribution name and import name don't have to match in Python packaging.

**Why we did this:** the old import path `from mangroveai import ...` collided with the `MangroveAI` backend repo directory. A previous attempt to rename the PyPI distribution to `mangrove-ai` was rejected by PyPI's similarity check (it normalizes by stripping non-alphanumerics, so `mangrove-ai` → `mangroveai` collides with the existing project we own). The compromise: keep the PyPI dist name as-is, rename only the import path.

**The shim:** `src/mangroveai.py` re-exports everything from `mangrove_ai` and emits a `DeprecationWarning` on import. It uses `sys.modules[__name__] = mangrove_ai` so submodule imports (`from mangroveai.models import X`) also forward. The compatibility shim is a single file to avoid a physical directory collision with the private engine on case-insensitive hosts. It is retained in v2.x for existing users; removal needs an explicitly announced future major release.

## Release flow (workflow_dispatch only — never push tags manually)

Python release preparation and publication are separate manual workflows. Neither
pushes a version commit to `main`; human-reviewed PRs own source changes.

1. Dispatch `.github/workflows/prepare-release.yml` from `main` with
   `bump=<patch|minor|major>`. It changes both version files on a
   `codex/release-vVERSION` branch, opens a version PR and explicitly dispatches
   offline CI (PRs opened with `GITHUB_TOKEN` do not trigger CI automatically).
2. Require the version PR's CI and human review, then merge through the normal
   PR process. Agents never merge. Preparation does not tag or publish.
3. After publication authorization, dispatch `.github/workflows/release.yml` from
   `main` with `version=VERSION`, exactly matching the two committed version files.
4. Publication checks source versions, tests and builds unchanged `github.sha`,
   exercises installed wheel/source artifacts, and checks PyPI/tag consistency.
   Only after validation does it create and push the exact tag at that same SHA.
5. Publication uses the repository's `PYPI_API_TOKEN`. Verify the actual PyPI files
   and GitHub Release afterward, then update consumer pins.

Never stamp versions during publication, push directly to main, or push tags
manually. A preexisting target tag or PyPI version requires release-state
reconciliation; it is not permission to overwrite a release.

The preparation workflow needs Actions write permission to dispatch offline CI and
repository permission to open PRs. No workflow was dispatched during implementation.
The package name stays `mangroveai`; `mangrove_ai` is its import path.

## Current release preparation and recovery

Published packages as of November 2, 2026: Python `mangroveai` 2.2.0 and
TypeScript `@mangrove-ai/sdk` 1.1.0. The reviewed source candidates here are
Python 2.3.0 and TypeScript 1.2.0; they are not published by a source commit.
The initial Markets-to-AI npm naming transition is historical and complete.
Preserve old Markets `@mangrove-ai/sdk` 0.x archives and their exact notices;
Markets now uses published `@mangrove-ai/markets` 0.4.0. Never publish the
abandoned `@mangrove-ai/client` candidate.

After source CI, human review/merge and publication authorization, Python uses
`release.yml` from main with `version=2.3.0`, matching both committed version
files. TypeScript uses `typescript-release.yml` from main with `version=1.2.0`
and first `dry_run=true`; authorized publication uses `dry_run=false`.
No agent pushes a tag manually or merges a PR. Keep the default-loss change in
[SDK PR82](https://github.com/MangroveTechnologies/MangroveAI-SDK/pull/82) /
[API PR1518](https://github.com/MangroveTechnologies/MangroveAI/pull/1518) separate: this candidate preserves the current default of four.
The new local-deployment helper requires the reviewed backend 7.11.0 or later capability
and actual serving acceptance before it is advertised as available.

The source version for an absent npm target must remain fresh main immediately
before upload. Build and test the unchanged source, require the actual bundled
npm-prepared `gitHead`, and bind the archive to SHA256/SHA512 integrity. An
existing npm version resumes only when name, repository, original source,
version, integrity and downloaded bytes match. Never overwrite a version, tag,
release or asset; do not move npm latest back to an older source.

Optional `release_commit` is for finishing an already published artifact from
its original full ancestor SHA. The current reviewed main controller verifies
that original source; a mutable ref, feature head or older unpublished source is
refused. The completed 1.1.0 recovery remains bound to its original 92f6d840 source,
not to a newer controller commit.

Only a just-accepted upload may wait for temporary metadata/archive HTTP 404s:
GET-only every 30 seconds under one shared ten-minute visibility deadline. Other
errors stop immediately, with no upload retry. Existing-artifact recovery and
preflight do not wait. GitHub's separate 120-second finalization budget begins
after npm bytes are verified, so registry processing cannot exhaust it early.
The controller creates or verifies the exact annotated version tag, GitHub
Release and checksum-bound assets only after registry verification. Historical
notice reads skip already matching notices; only exact approved old versions
can be updated. Package publication never proves backend serving or paid/live
execution. No release workflow is dispatched merely to prepare this source.

## Pre-tag PyPI similarity check (if EVER renaming the dist)

If you're considering changing `pyproject.toml` `name = "mangroveai"` to anything else, run this check first:

```python
import re, urllib.request
candidate = "mangrove-ai-sdk"  # or whatever you're proposing
normalized = re.sub(r'[^a-zA-Z0-9]', '', candidate).lower()
try:
    urllib.request.urlopen(f"https://pypi.org/pypi/{normalized}/json", timeout=5)
    print(f"COLLISION: PyPI has a project at '{normalized}'. The upload will fail.")
except urllib.error.HTTPError as e:
    if e.code == 404:
        print(f"OK: '{normalized}' is free on PyPI")
```

If the normalized form collides, the upload will fail with `400 "name is too similar to an existing project"` — even if you own the colliding project. PyPI's similarity rule predates the legitimate-rename case.

## Local development

```bash
# In a fresh venv
pip install -e ".[dev]"

# Tests (mock transport; no network)
pytest tests/ --ignore=tests/integration

# Live integration (real prod API key required)
MANGROVE_API_KEY=prod_... pytest tests/integration
```

## Don't

- Don't push tags manually — use `gh workflow run release.yml`.
- Don't rename the PyPI distribution name without running the similarity check first.
- Don't remove the `src/mangroveai.py` compatibility shim without an explicitly announced future major release — it's load-bearing for users still on the old import path.
- Don't add new SDK functionality to `src/mangroveai.py` — that's the shim only. New code goes in `src/mangrove_ai/`.

The canonical inventory excludes one deprecated SDK compatibility alias, `POST /api/v1/backtests/`, retained from TypeScript1.1.0. It inherits the canonical backtest contract while preserving its original HTTP path; new callers should use `POST /api/v1/backtests`.
