# Python SDK issue 66 release handoff

Issue: https://github.com/MangroveTechnologies/MangroveAI-SDK/issues/66

## Current TypeScript naming decision (2026-11-02)

The user selected `@mangrove-ai/sdk` for MangroveAI and `@mangrove-ai/markets`
for MangroveMarkets. This source prepares the AI package at 1.0.0; the separate
Markets source prepares 0.4.0. `@mangrove-ai/client` was an unpublished candidate
and will not be published. No alias is introduced.

Published `@mangrove-ai/sdk` 0.1.2, 0.2.0 and 0.3.0 are historical Markets
packages. Their bytes and provenance stay intact; AI 1.0.0 is a breaking product
move rather than a compatible Markets upgrade. See the [migration notice](typescript-package-migration.md).
After both source PRs are human-merged, verify the Markets 0.4.0 publication
before the AI 1.0.0 publishing run. The existing manual workflow file remains
`typescript-release.yml`, with inputs `version=1.0.0` and `dry_run=true` for
validation, then `dry_run=false` for authorized publication from `main`.
The workflow verifies exact npm archive bytes and source metadata before creating
or reading back annotated `typescript-v1.0.0`, the GitHub Release and immutable
checksum assets. The three exact historical Markets versions receive native
migration notices last; no whole-name deprecation is allowed. For a partial
release, `release_commit` may select only a full original main-ancestor SHA.
Existing matching publication/tag/release/assets resume; mismatches fail without
overwrite. Do not dispatch the older workflow/source revision for `@mangrove-ai/client`.
Python stays at its published 2.1.0 version. Source, registry publication,
installed consumers, backend serving and live acceptance remain separate facts.
The dated section below preserves the previous naming and publication record.

For a new unpublished version, the selected source must still be fresh `main`
immediately before publishing. An older main ancestor is accepted only to finish
an already published artifact whose exact source and bytes were verified. It
cannot start a new publication or move npm `latest` back to stale source.

## Historical publication status (2026-11-01)

Python SDK 2.1.0 was published from main commit
`b879241e10c283c45617bf83a2591728b2ccfac0` by the
[successful release workflow](https://github.com/MangroveTechnologies/MangroveAI-SDK/actions/runs/41242672813).
The [v2.1.0 GitHub Release](https://github.com/MangroveTechnologies/MangroveAI-SDK/releases/tag/v2.1.0)
and [PyPI wheel and source distribution](https://pypi.org/project/mangroveai/2.1.0/#files)
exist; both public artifact hashes and isolated installations were verified.
[Agent PR230](https://github.com/MangroveTechnologies/mangrove-agent/pull/230)
has merged with a 2.1.0 pin. API acceptance-harness pin updates are being reviewed
in [API PR1502](https://github.com/MangroveTechnologies/MangroveAI/pull/1502).

The TypeScript candidate `@mangrove-ai/client` 0.1.0 remains unpublished. Its
[publication run](https://github.com/MangroveTechnologies/MangroveAI-SDK/actions/runs/41271133519)
passed contract generation, type checking, tests and package checks, then stopped
because the effective `NPM_TOKEN` was empty. A maintainer must configure a
publisher credential with access to that package before retrying publication.

A fresh public registry readback on 2026-11-01 confirms Python `mangroveai`
2.1.0 exists, npm `@mangrove-ai/client` returns 404, and the separate Markets
package `@mangrove-ai/sdk` has latest version 0.3.0. These are dated observations,
not permanent package properties or evidence that an unclaimed name is reserved.
At that checkpoint, the MangroveAI TypeScript implementation was version 0.1.0.
Its 264 generated method/path keys include 10 v2 operations, with named helpers
for users, signals, strategy workflow and backtesting; it is not Python helper
parity. Registry publication and its installed-artifact readback remain separate.

Publication does not establish that the API revision is deployed, that a live
business request succeeds, or that an installed client has updated. The original
repair/release-preparation record below is historical; its 2.0.0 version and
pre-publication statements describe that earlier source snapshot.

This branch repairs the existing `mangroveai` distribution. Its import remains
`mangrove_ai`; `mangroveai` remains a compatibility shim. It is the Python client
for the MangroveAI API. MangroveMarkets' Python package is a separate API client.

## Review scope and existing work

The branch starts at main 41c943d4e9e212ea471c98f11ccd3d478b4b45ca and locally
merges existing PR 60 (7b7cd0a2c64d7676db9b9e977e93b3e8b47946af) and PR 65
(72905fe84e210fb7138dedd85d44af3ed55745b6). Their remote branches are unchanged.

- https://github.com/MangroveTechnologies/MangroveAI-SDK/pull/60
- https://github.com/MangroveTechnologies/MangroveAI-SDK/pull/65

Both confirmed-execution v2 event acknowledgments from PR 60 and the confirmed
versus proposed trade models from PR 65 are preserved. Review their backend
deployment prerequisites before advertising those features. They do not place
broker orders. Existing Oracle contract fixtures from PR 60 remain intact.

The issue adds timeout, configuration, session-authentication, route, position
filter, error-handling, Python minimum-version and packaging repairs. Tests use
real SDK/httpx request construction with intercepted HTTP responses. They do not
make authenticated business calls or verify production execution enforcement.

Mangrove owns enforcement of user limits and approval policy using current
market/account conditions. The SDK neither reimplements that policy nor treats
an LLM assertion, caller confirmation flag or local result filter as enforcement.
The `max_drawdown` result filter inherited from PR 60 is research screening only.

## Compatibility and migration

- API keys use `Authorization: Bearer ...`. API-key 401 responses do not trigger
  session refresh. Firebase login establishes a session on the same client.
- Current refresh requires scoped `mg_refresh` and `mg_csrf` cookies and a
  matching `X-CSRF-Token`, without JSON. A supplied body refresh token now raises
  a clear local error. Older omitted/null login body tokens remain accepted.
- Development has no verified usable public default. Configure `base_url` or
  `MANGROVE_BASE_URL`, ending in `/api/v1`. v2 derives the sibling `/api/v2` path.
  `test_` keys require a configured origin or explicit local environment.
  The Knowledge Base retains its separate `kb_base_url` setting.
- `execution.update_account`, `execution.get_position`,
  `crypto_assets.risk_analysis` and retired WhaleAlert compatibility methods fail
  before HTTP. No current backend routes implement them.
- `list_positions(open_only=False)` returns both states; legacy `status="closed"`
  filters only the server page. Page offsets still refer to all server rows.
- Use `examples/first_call.py` for one usage request from private configuration.
  The separate stdlib HTTP/MCP example is an alternative, not full SDK coverage.

## Contract and verification limits

The API canonical schema and projected Oracle proxy contract are separate
inputs. Schema validity alone does not establish full endpoint/model coverage:
legacy endpoints still have incomplete response schemas, and the Oracle proxy
transforms some retail responses. Do not regenerate all Python models blindly
or claim that every service method has an authenticated live contract check.

The offline suites cover existing service models, actual Bearer headers, timeout
propagation, errors, cookie path/origin scoping, refresh retry behavior, malformed
responses and pagination. CI now also installs the built wheel and source archive
in fresh environments and exercises a usage/error/Oracle-pagination fixture with
the legacy imports. Live integration remains manually dispatched and separate.

## Release sequence after explicit publication approval

No package, tag, PR or deployment was published as part of the local repair.
Version files intentionally remain 2.0.0; a manual preparation workflow opens the
reviewed version PR before separate publication. Local 2.0.0 artifacts are unpublished
review builds and are not the bytes currently served by PyPI.

1. Reconcile and review PR 60/65 with this combined branch; avoid landing duplicate
   overlapping implementations. Merge only through the authorized review flow.
2. Require offline CI on 3.10 and 3.12, the installed-distribution gate, and the
   matching backend release for any confirmed-execution features being announced.
3. Dispatch `prepare-release.yml` from main with the agreed semver bump. Review
   and merge its version PR after CI; the workflow explicitly dispatches CI because
   PRs created by `GITHUB_TOKEN` do not start it automatically. After separate
   publication authorization, dispatch `release.yml` from main with that exact
   committed `version`. It builds unchanged source and only tags the validated
   `github.sha`; it never pushes a version commit to main. Never push tags manually.
   The workflow checks current PyPI/tag consistency and installed artifacts before
   creating a release tag.
4. Verify the exact new PyPI version, wheel/source metadata, download hashes and
   published-package first-call snippet. Then update consumer pins and docs as
   one release handoff. `mangrove-agent/server/requirements.lock` currently pins
   2.0.0; its requirements range is `>=2.0.0,<3.0.0`. No consumer was edited here.
5. Publish SDK-first examples and the onboarding email only after Python/TS
   package availability, deployed contract and public docs agree.

Local reproducible checks:

```bash
ruff check src tests examples/first_call.py scripts/check_installed_distribution.py
pytest tests --ignore=tests/integration
python -m build
python -m venv .venv-wheel
.venv-wheel/bin/pip install dist/*.whl
.venv-wheel/bin/python -I scripts/check_installed_distribution.py
python -m venv .venv-sdist
.venv-sdist/bin/pip install dist/*.tar.gz
.venv-sdist/bin/python -I scripts/check_installed_distribution.py
```
