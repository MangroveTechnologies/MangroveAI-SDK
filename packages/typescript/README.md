# MangroveAI TypeScript client

Candidate `@mangrove-ai/client` 0.1.0 for Node.js 20+. This package has not been
published to npm. The final name and publishing rights need maintainer verification.
Install a reviewed local tarball while evaluating it:

```sh
npm install ./mangrove-ai-client-0.1.0.tgz
```

This is the MangroveAI REST client. `@mangrove-ai/sdk` is the separate Markets
client. The existing Python distribution is `mangroveai`, imported as `mangrove_ai`.

## First request

Keep the API key in server-side configuration, outside browser bundles, prompts
and logs. The constructor can read `MANGROVE_API_KEY` or accept the key directly.

```js
import { MangroveAI, APIError } from '@mangrove-ai/client';

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

`client.request(operation, options)` provides generated path, parameter, body and
response types for the reviewed REST and Oracle proxy contracts. Operation keys
include the HTTP method and exact versioned path:

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

Updating contracts is a reviewed change. Export both documents from the backend's
`scripts/export_developer_contracts.py` with network blocked, then regenerate the
TypeScript declarations and inspect the capability diff. Preserve the recorded
source revisions and hashes. Changes to the pinned inputs without regeneration
fail CI. A source-only check cannot detect an unobserved deployment change.

Package versioning is independent of Python. Verify the candidate name, exact
source commit, compatibility, installed tarball examples and required server
deployment before a maintainer publishes. Then read back the registry artifact
and update the consumer pins and public guide. Do not advertise this candidate as
available from npm until those steps succeed.

The separate `Release TypeScript client` workflow is manual, accepts only the
reviewed `main` branch and defaults to a dry run. Its selected version must match
the manifest and must not already exist in the registry. It always validates
contracts, builds, tests and installs the tarball. Maintainers must configure
the protected `npm-release` environment and its `NPM_TOKEN`, confirm namespace
rights and the final package name, and explicitly choose a publishing run.
No release workflow was dispatched during implementation.
