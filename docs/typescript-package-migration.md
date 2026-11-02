# TypeScript package migration: MangroveAI and Markets

Naming decision: 2026-11-02. These source changes are not registry publication.

| Product | Package to use after verified publication | Public import |
|---|---|---|
| MangroveAI | `@mangrove-ai/sdk` 1.0.0 | `import { MangroveAI } from '@mangrove-ai/sdk'` |
| MangroveMarkets | `@mangrove-ai/markets` 0.4.0 | `import { MangroveClient } from '@mangrove-ai/markets'` |

Python names and versions do not change: `mangroveai` 2.1.0 imports as
`mangrove_ai`; `mangrovemarkets` 1.1.1 imports as `mangrove_markets`.

## Existing Markets applications

Published `@mangrove-ai/sdk` versions 0.1.2, 0.2.0 and 0.3.0 are Markets clients.
Those artifacts remain historical and are not overwritten. The new AI 1.0.0
package does not preserve their API, exports, configuration or product semantics.
Do not upgrade an existing Markets app to `@mangrove-ai/sdk` 1.x.

Once the new Markets package is published and verified, change the dependency to
`@mangrove-ai/markets` 0.4.0 and keep its existing `MangroveClient` import name:

```typescript
import { MangroveClient } from '@mangrove-ai/markets';
```

Until then, install the reviewed `mangrove-ai-markets-0.4.0.tgz` archive in a test
consumer using its actual path. Do not treat an unpublished name as available
from the registry. Pin and inspect package identities in the lockfile. Normal
0.x caret ranges do not select 1.0.0, but an unpinned `latest` install can select a
different major product after publication. There is no cross-product export alias.

## MangroveAI applications

The prior `@mangrove-ai/client` 0.1.0 archive was an unpublished review candidate.
It will not be published or retained as a registry alias. Replace that local
dependency and import with the reviewed `@mangrove-ai/sdk` 1.0.0 archive, or the
exact 1.0.0 registry release after its publication is verified:

```typescript
import { MangroveAI } from '@mangrove-ai/sdk';
```

The AI runtime, public class and generated operation contracts are preserved.
Its named helpers are `users`, `signals`, `strategyWorkflow` and `backtesting`,
with generic typed `request` for the reviewed REST declarations. It is not Python
helper parity or a Markets client. MCP/OAuth discovery, the separate legacy KB
host, x402 signing and SSE consumption remain separate interfaces. See the
[TypeScript guide](../packages/typescript/README.md).

When both products are needed, install both new package names explicitly and
keep their credentials and configured API URLs separate. Python AI expects a
versioned `/api/v1` base, Python Markets expects an origin, and AI TypeScript
accepts an origin or versioned base. Do not share one global base override across
products or assume their API keys are interchangeable. Mangrove owns deterministic
risk management based on live market and account conditions; SDKs preserve its
decisions rather than running their own enforcement policy.

## Release order and recovery

1. Review and human-merge both source PRs. No package publication follows merely
   from a source claim, a local tarball or this migration page.
2. Publish and verify the exact `@mangrove-ai/markets` 0.4.0 artifact from the
   Markets repository first. Confirm its real `MangroveClient` import and release
   identity before changing application pins.
3. From reviewed SDK `main`, use `.github/workflows/typescript-release.yml` with
   `version=1.0.0`, first `dry_run=true`, then `dry_run=false` for the authorized
   release. It checks package/lock/repository identity, derives real npm `gitHead`
   from the normal checkout, and verifies the Markets prerequisite. It publishes
   only an absent AI version, then downloads the registry archive and checks its
   SHA512 and SHA-256 against the exact source build.
4. The native workflow creates or reads back annotated `typescript-v1.0.0`, checks
   its dereferenced source commit, and creates/verifies the source/checksum-bound
   GitHub Release and immutable assets. It then applies migration notices only to
   `@mangrove-ai/sdk@0.1.2`, `@mangrove-ai/sdk@0.2.0` and `@mangrove-ai/sdk@0.3.0`.
   There is no whole-name deprecation, unpublish or forced tag/asset overwrite.
5. Verify installed consumers and reference material separately. For a partial
   release, set `release_commit` to the original full main-ancestor SHA. The
   current main workflow rebuilds that source and resumes only an exactly
   matching npm `gitHead`/archive, annotated tag and release/assets. Missing assets
   can be completed; a conflicting identity stops. Do not invent another version
   or retag an artifact to work around an uncertain result.

A package release is separate from backend serving, OAuth availability, reference
publication and live acceptance. An uncertain release attempt requires registry
and artifact reconciliation before another attempt; it is not permission to
publish a different version or change a tag automatically.

For a new unpublished version, the selected source must still be fresh `main`
immediately before publishing. An older main ancestor is accepted only to finish
an already published artifact whose exact source and bytes were verified. It
cannot start a new publication or move npm `latest` back to stale source.
