# MangroveAI Python SDK

Python SDK for the MangroveAI HTTP API (strategies, signals, backtests, oracle, copilot, etc.). Published to PyPI as `mangroveai`. Source lives at `src/mangrove_ai/`.

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

**The shim:** `src/mangroveai/__init__.py` re-exports everything from `mangrove_ai` and emits a `DeprecationWarning` on import. It uses `sys.modules[__name__] = mangrove_ai` so submodule imports (`from mangroveai.models import X`) also forward. The shim is scheduled for removal in v2.0.0.

## Release flow (workflow_dispatch only — never push tags manually)

The release pipeline is `.github/workflows/release.yml`, triggered via `workflow_dispatch` with a `bump` input (`patch`/`minor`/`major`). The workflow OWNS the entire bump → tag → build → publish lifecycle:

1. Reads `bump=<patch|minor|major>` input.
2. Computes next version from the latest `v*` tag.
3. Updates `pyproject.toml` `version` + `src/mangrove_ai/_version.py` `__version__`.
4. Commits, tags `v<version>`, pushes to main with `--follow-tags`.
5. Builds wheel via `python -m build`.
6. Verifies the built wheel's METADATA `Version` field matches the computed version.
7. Publishes to PyPI via `pypa/gh-action-pypi-publish@release/v1` using `secrets.PYPI_API_TOKEN`.
8. Creates a GitHub Release via `softprops/action-gh-release@v2`.

**Never push a tag manually.** Doing so:
- Skips the version bump (so `pyproject.toml` and the tag disagree)
- Skips the PyPI publish (tag exists with no corresponding artifact — orphan)
- Skips the GitHub Release creation

We had to recover from exactly this in May 2026 (orphan tags `v1.0.0` + `v1.0.1` that never published; cleanup required `gh api DELETE /repos/.../git/refs/tags/<name>` because `git push --delete` is hooked by the portfolio's branch-protection script).

To release: `gh workflow run release.yml -f bump=patch --repo MangroveTechnologies/MangroveAI-SDK`. Wait for completion. Verify on PyPI public + check the Releases page.

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
- Don't remove the `src/mangroveai/__init__.py` shim before v2.0.0 — it's load-bearing for users still on the old import path.
- Don't add new code under `src/mangroveai/` — that's the shim only. New code goes in `src/mangrove_ai/`.
