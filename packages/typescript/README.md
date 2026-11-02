# MangroveAI TypeScript SDK

Server-side `@mangrove-ai/sdk` for Node.js 20+, imported as
`import { MangroveAI } from '@mangrove-ai/sdk'`. This is the MangroveAI API
client in version 1.x. The separate Markets client moves to `@mangrove-ai/markets`;
Python MangroveAI uses the PyPI distribution `mangroveai` and import `mangrove_ai`.

**Major product migration:** `@mangrove-ai/sdk` 0.1.2, 0.2.0 and 0.3.0 are
historical Markets packages. Version 1.0.0 is the MangroveAI SDK and does not
provide their `MangroveClient` API. Markets applications must install
`@mangrove-ai/markets` 0.4.0 after that release is verified, or use its reviewed
archive. Read the [migration notice](https://github.com/MangroveTechnologies/MangroveAI-SDK/blob/main/docs/typescript-package-migration.md)
before changing a pin. The old `@mangrove-ai/client` candidate was never published
and will not become a registry alias.

Check the [dated repository release status](https://github.com/MangroveTechnologies/MangroveAI-SDK/blob/main/docs/issue-66-release-handoff.md)
for registry availability and verified versions. Source, a local package and a
published npm release are separate states. For evaluation before a registry
release, build and install a reviewed local tarball:

```sh
npm ci --ignore-scripts --prefix packages/typescript
npm pack ./packages/typescript
```

Run these commands from the source repository root with Node.js 20+. The archive
is written there, with a name based on that revision's `package.json` version.
Then install that reviewed archive in the consuming project, using its actual path:

```sh
npm install /path/to/reviewed/mangrove-ai-sdk-1.0.0.tgz
```

When installing a registry release, verify its exact version and package identity
first.

## First request

Keep the API key in server-side configuration, outside browser bundles, prompts
and logs. The constructor can read `MANGROVE_API_KEY` or accept the key directly.
Development requires an explicit `baseUrl` or `MANGROVE_BASE_URL`. Keys beginning
with `test_` also require an explicit origin or `environment: 'local'`; they never
default to production. This selects routing, not server permission enforcement.

```js
import { MangroveAI, APIError } from '@mangrove-ai/sdk';

const client = new MangroveAI({ apiKey: process.env.MANGROVE_API_KEY, timeoutMs: 30_000 });
try {
  const metrics = await client.users.getMyMetrics();
  console.log({ messages: metrics.messages_count });
} catch (error) {
  if (error instanceof APIError) {
    console.error({ status: error.status, code: error.code, correlationId: error.correlationId });
  } else {
    throw error;
  }
}
```

This sends one Bearer-authenticated usage read. It does not create a wallet,
launch compute, connect a broker, invoke an MCP tool or send a payment.

## Supported surface

The named helpers are `users`, `signals`, `strategyWorkflow` and `backtesting`.
Other declared REST operations use `client.request(operation, options)`, with
generated path, parameter, body and response types. This is not Python helper
parity. The current classification has 264 core/Oracle proxy method/path keys,
including 10 v2 operations: 261 JSON/no-content, one separate redirect flow and
two streaming/non-JSON operations. Counts describe pinned declarations, not live
endpoint acceptance. The JSON transport does not perform the redirect or consume
those streams. Operation keys include the HTTP method and exact versioned path:

```ts
const result = await client.request('GET /api/v1/strategies/{strategy_id}', {
  path: { strategy_id: 'the-strategy-id' },
});
```

The contracts and complete operation classification live in
`contracts/mangroveai/` in the source repository. Types describe server schema
declarations. They are not proof that every deployed response matches its model.
Unmodelled responses and legacy Raw JSON fields remain `unknown`. The transport
checks status, JSON, size and deadline; the metrics and pagination helpers also
validate their envelopes. Application code must narrow an opaque result.

The server's canonical strategy workflow schemas generate method names such as
`client.strategyWorkflow.getStrategy({ body: { strategy_id } })` and
`client.strategyWorkflow.saveStrategy({ body: ... })`. These helpers pass requests
to the same server operations; they do not copy composition, ranking or risk rules.

Mangrove owns deterministic risk management based on live market and account
conditions. The SDK carries requests and preserves the server's decisions and
results. It does not implement trading policy or establish that every execution
path enforces that product contract.

The Oracle projection uses the API proxy origin, not a private Oracle service
host. Its allowlist and HTTP methods come from the proxy. Some retail adapters
transform upstream backtest, simulation, experiment and condition envelopes;
their types remain opaque, with upstream declarations identified separately.
Server scopes, tenant access, entitlements and billing still apply.

The generated `ExecutionConfiguration` type describes normalized authoring
values from the backend's canonical configuration schema, including cooldown
fields and their required declarations. Transport inputs also accept a legacy
object escape hatch, preserving server compatibility with numeric strings and
other existing shapes. To read the server's schema and glossary explicitly:

```ts
const config = await client.request('GET /api/v1/config/execution-config-schema', {});
console.log(config.json_schema);
```

This is one server request and may be billable. The client does not fetch it
automatically, prevalidate execution configuration or implement risk policy.
Normalized authoring guidance is separate from the server's accepted transport
input; nested guidance is not a claim that the HTTP boundary enforces all fields.

The generic JSON transport does not consume SSE, binary or HTML responses. It
rejects those formats instead of misrepresenting them as JSON. MCP discovery,
MCP OAuth, x402 signing and the separate legacy KB host are separate interfaces.
There is no automatic payment or automatic retry. A failed non-idempotent request
may need a server status read before the caller decides whether to repeat it.

## Pagination and asynchronous jobs

```js
for await (const signal of client.signals.listIter({ limit: 100, category: 'momentum' })) {
  console.log(signal.name);
}
```

Pagination follows the server's `next_offset` rather than the requested page size.
Malformed, contradictory or repeated pages raise. Each page is a separate request
and may be billable. Stop iteration when the application has what it needs.

`client.backtesting.submit(body)` makes an explicit submission;
`getStatus(backtestId)` reads one status. `wait(backtestId, { timeoutMs,
pollIntervalMs, signal })` only polls that existing job. It returns completed,
failed and cancelled results without replacing them with a success. It enforces
one total polling deadline and never resubmits the job. Obtain the appropriate
approval before submitting compute; the SDK does not infer approval.

## Configuration and errors

`baseUrl` or `MANGROVE_BASE_URL` accepts an API origin or its `/api/v1` or
`/api/v2` base. Both API versions stay on that origin. Production defaults to
`https://api.mangrovedeveloper.ai`. Development keys require an explicit origin;
the client does not fall back to production. HTTPS is required except for
loopback tests. API redirects are refused.

`timeoutMs` is a positive integer, default 30000. One deadline covers response
headers and the entire JSON body. `maxResponseBytes` defaults to 8 MiB and is
enforced against both the declared size and actual chunks. Request controls
accept an AbortSignal and a per-request timeout. An injected `fetch` can supply
test transport or a caller-managed cookie jar. Native Node fetch does not retain
session cookies; the recommended authentication path is an API key. A manual
session refresh requires the same session's Cookie and X-CSRF-Token headers and
has no JSON token body.

Errors include `APIError`, `ConfigurationError`, `MalformedResponseError`,
`RequestTimeoutError`, `RequestAbortedError` and `NetworkError`. `APIError`
exposes HTTP status, safe code/message, correlation ID and Retry-After. Its
non-enumerable `response` retains the redacted error envelope; `headers` retains
payment challenge/recovery and authentication headers. Inspect these explicitly
when handling a server decision. Default JSON serialization excludes them and
never includes request credentials. No payer or automatic recovery is invoked.

## Build and release checks

From the repository root:

```sh
python3 scripts/generate_typescript_contract.py --check
npm ci --ignore-scripts --prefix packages/typescript
npm run typecheck --prefix packages/typescript
npm test --prefix packages/typescript
node packages/typescript/test/packed-artifact.mjs
```

Updating contracts is a reviewed change. Export all three documents from the backend's
`scripts/export_developer_contracts.py` with network blocked, then regenerate the
TypeScript declarations and inspect the capability diff. Preserve the recorded
source revisions and hashes. Changes to the pinned inputs without regeneration
fail CI. A source-only check cannot detect an unobserved deployment change.

Package versioning is independent of Python. Verify the candidate name, exact
source commit, compatibility, installed tarball examples and required server
deployment before a maintainer publishes. Then read back the registry artifact
and update the consumer pins and public guide. Do not advertise a source candidate as
available from npm until those steps succeed.

The separate `Release MangroveAI TypeScript SDK` workflow is manual, runs from
reviewed `main` and defaults to `dry_run=true`. Its selected version must match
the manifest and lock, identify this repository's `@mangrove-ai/sdk` with major
version at least 1, and pass installed-package checks. Publishing first requires
verified `@mangrove-ai/markets` 0.4.0. It uses directory publication after official
npm preparation proves the selected source `gitHead`; it does not guess that
publishing a tarball adds source metadata.

After publishing, actual npm archive bytes must match the local SHA512 and
SHA-256. The native workflow then creates/verifies annotated
`typescript-v1.0.0`, a source/checksum-bound GitHub Release and immutable tarball,
checksum and provenance assets. Exact old Markets versions 0.1.2, 0.2.0 and 0.3.0
receive migration notices only after those checks. No package version, tag or
asset is overwritten, and the whole package name is never deprecated.

An optional full main-ancestor `release_commit` supports an interrupted release.
An already published artifact can resume only when its name, repository,
`gitHead`, integrity and downloaded bytes match the rebuilt original source.
Existing tags are dereferenced to their annotated commit; matching release
bodies/assets are retained and missing assets can be completed. Conflicts stop.
Dry runs never publish, tag, create releases or deprecate versions. Package
publication remains separate from deployed API and live acceptance.

For a new unpublished version, the selected source must still be fresh `main`
immediately before publishing. An older main ancestor is accepted only to finish
an already published artifact whose exact source and bytes were verified. It
cannot start a new publication or move npm `latest` back to stale source.
