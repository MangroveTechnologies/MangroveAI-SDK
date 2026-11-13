# TypeScript package migration: MangroveAI and Markets

Naming decision: 2026-11-02. The initial product rename is complete.
Registry checkpoint: AI 1.1.0 and Markets 0.4.0 are published; this source prepares
AI 1.2.0, which remains a candidate until its official release is verified.

| Product | Published package | Public import |
|---|---|---|
| MangroveAI | `@mangrove-ai/sdk` 1.1.0 | `import { MangroveAI } from '@mangrove-ai/sdk'` |
| MangroveMarkets | `@mangrove-ai/markets` 0.4.0 | `import { MangroveClient } from '@mangrove-ai/markets'` |

Published Python names: `mangroveai` 2.4.2 imports as
`mangrove_ai`; `mangrovemarkets` 1.1.1 imports as `mangrove_markets`.

## Existing Markets applications

Published `@mangrove-ai/sdk` versions 0.1.2, 0.2.0 and 0.3.0 are Markets clients.
Those artifacts remain historical and are not overwritten. The new AI 1.0.0
package does not preserve their API, exports, configuration or product semantics.
Do not upgrade an existing Markets app to `@mangrove-ai/sdk` 1.x.

For an existing Markets application, change the dependency to
`@mangrove-ai/markets` 0.4.0 and keep its existing `MangroveClient` import name:

```typescript
import { MangroveClient } from '@mangrove-ai/markets';
```

For an unpublished future patch, use a reviewed archive until its own registry
release is verified. Pin and inspect package identities in the lockfile. Normal
0.x caret ranges do not select 1.0.0, but an unpinned `latest` install can select a
different major product after publication. There is no cross-product export alias.

## MangroveAI applications

The prior `@mangrove-ai/client` 0.1.0 archive was an unpublished review candidate.
It will not be published or retained as a registry alias. Replace that local
dependency and import with the published `@mangrove-ai/sdk` 1.1.0 package, or a reviewed local archive for an
unpublished candidate:

```typescript
import { MangroveAI } from '@mangrove-ai/sdk';
```

The AI runtime, public class and generated operation contracts are preserved.
The 1.2.0 candidate adds `strategies.localDeployment`; published 1.1.0 has named
`users`, `signals`, `strategyWorkflow` and `backtesting` helpers,
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

## Current release order and recovery

The first Markets 0.4.0 / AI 1.0.0 product migration is historical and complete;
there is no need to publish either original version again. The three exact old
Markets versions keep their migration notices, with already matching notices
skipped by the AI controller. Never publish `@mangrove-ai/client`.

1. Review the current source candidates, exact-head CI and actual installed
   artifacts. New local-deployment coverage in Python 2.3.0 / TypeScript 1.2.0
   requires backend 7.11.0 or later and its actual serving acceptance first.
   The reviewed API1525 schema defaults to two consecutive losses; the older
   [SDK PR82](https://github.com/MangroveTechnologies/MangroveAI-SDK/pull/82) and
   [API PR1518](https://github.com/MangroveTechnologies/MangroveAI/pull/1518)
   proposals are closed and are not separate dependencies.
2. Human-merge reviewed SDK source. From actual current main, run the native
   `typescript-release.yml` with `version=1.2.0`, first `dry_run=true`, then
   authorized publication with `dry_run=false`. Python uses its separate
   version-preparation workflow for the next unpublished version, then
   `release.yml` with that exact merged version. Python 2.4.2 is already published
   and must not be uploaded again with changed bytes.
3. The TypeScript controller checks the actual source, npm-prepared gitHead,
   identity and archive checksums. Only an absent target may be uploaded from
   fresh main. A just-accepted upload can wait through GET-only metadata/archive
   HTTP 404 processing delays under one shared ten-minute budget. Other failures
   stop without another upload.
4. Verify actual registry bytes, source, annotated version tag, GitHub Release
   and immutable assets. Existing matching objects are reused; conflicts fail
   without overwrite. GitHub's separate 120-second budget starts after npm bytes
   have been verified. Complete matching historical notices cause no deprecate
   command; the controller owns the exact approved scope and message.
5. Update and test affected consumers after actual registry publication. For an
   interrupted already-published release, `release_commit` may select only its
   original full main-ancestor SHA. The current main controller verifies that
   original artifact; an older source cannot start a new publication or move
   latest backwards. The completed 1.1.0 recovery remains tied to original 92f6d840.

A package release is separate from backend serving, OAuth availability, reference
publication and live acceptance. Cloud/domain/venue migration and frontend
publication remain held. No tag, package, deployment or notice mutation is
performed merely by preparing this source.
