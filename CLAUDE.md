# MangroveAI SDKs: Python and TypeScript

This repository contains clients for the public MangroveAI services in both
languages. Keep their package identities and capabilities distinct:

- Python: PyPI `mangroveai`, import `from mangrove_ai import MangroveAI`, source
  `src/mangrove_ai/`. Python 2.1.0 is published; see the dated release handoff.
- TypeScript: npm identity `@mangrove-ai/client`, import
  `import { MangroveAI } from '@mangrove-ai/client'`, source `packages/typescript/`.
  Read [its guide](packages/typescript/README.md) and the [dated release status](docs/issue-66-release-handoff.md)
  before claiming registry availability. At the 2026-11-01 checkpoint, 0.1.0 is
  implemented but unpublished; reviewed local tarballs are supported for evaluation.
- `@mangrove-ai/sdk` is the separate MangroveMarkets client, not this API's
  TypeScript package. Do not rename, alias or repurpose either package.

TypeScript provides named `users`, `signals`, `strategyWorkflow` and `backtesting`
helpers and a generated generic `request(operation, options)` surface, not
Python method parity. The pinned public classification contains 264 core/Oracle
proxy method/path operations including 10 v2: 261 JSON/no-content, one separate
redirect flow and two streaming/non-JSON operations. Counts describe declarations,
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

**The shim:** `src/mangroveai/__init__.py` re-exports everything from `mangrove_ai` and emits a `DeprecationWarning` on import. It uses `sys.modules[__name__] = mangrove_ai` so submodule imports (`from mangroveai.models import X`) also forward. The shim is retained in v2.x for existing users; removal needs an explicitly announced future major release.

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
- Don't remove the `src/mangroveai/__init__.py` compatibility shim without an explicitly announced future major release — it's load-bearing for users still on the old import path.
- Don't add new code under `src/mangroveai/` — that's the shim only. New code goes in `src/mangrove_ai/`.
