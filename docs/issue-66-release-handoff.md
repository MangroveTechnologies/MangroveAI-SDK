# Python SDK issue 66 release handoff

Issue: https://github.com/MangroveTechnologies/MangroveAI-SDK/issues/66

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
   Configure required reviewers on `pypi-release` before publishing. The gate checks
   current PyPI/tag consistency and installed artifacts before creating a release tag.
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
