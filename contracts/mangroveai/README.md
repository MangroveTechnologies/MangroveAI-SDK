# Shared MangroveAI contracts

These are pinned generation inputs and synthetic HTTP fixtures for the Python
and TypeScript clients. `provenance.json` records the backend source commit,
source hashes and exported-document hashes. No real user, API key, session token
or account record belongs here.

`openapi.json` preserves the registered RESTX v1/v2 contract in its public OpenAPI 3.1 projection,
including the source-declared x402 alternatives and payment metadata.
`oracle-proxy-openapi.json` uses OpenAPI 3.1 and describes only upstream paths
reachable through the actual MangroveAI proxy allowlist and forwarded methods.
Its servers point at MangroveAI, not private upstream deployment hosts.

`execution-config.schema.json` is the backend's normalized authoring schema,
derived from its parameter metadata, defaults and shared required-field
declarations. The REST and MCP transport projections preserve accepted legacy
objects; `x-mangrove-authoring-schema` carries authoring guidance separately.
Nested schema guidance does not imply that the HTTP boundary validates every
nested field. Python exposes the additive schema from an explicit configuration
request; TypeScript exports its generated `ExecutionConfiguration` type and
retains a legacy-object transport escape hatch. Neither client automatically
fetches configuration or runs trading-risk validation.

`ExecutionConfiguration` names `cooldown_model` and the partial `circuit_breaker`
object, including its nine server-declared controls. Python preserves their
defaults and nested glossary in the explicit schema response. The default trades
schema omits the four bars-only keys (`cooldown_config`, `cooldown_bars`,
`daily_momentum_limit`, `weekly_momentum_limit`), matching the canonical server.
Explicit bars/legacy objects remain transport-compatible. The shared default
fixture comes from the offline API1525 source service; the separate bars fixture
comes from the same service with explicit `cooldown_model="bars"` and verifies
legacy response compatibility without claiming a public mode selector. Both
fixtures carry the producer's default of two consecutive losses. These authoring
declarations do not add a client-side trading gate; the legacy transport escape
hatch and server-owned risk decisions remain unchanged.

`local-deployment-not-ready.json` is a synthetic stored strategy snapshot with
explicit legacy execution settings, including a loss limit of four. That stored
value is not the current server default.

`coverage.json` enumerates every generated REST operation, response modelling
status and matching direct Python transport bindings. Python wrappers delegating
to another method are not separate routes; an empty direct-binding list is not
proof that Python cannot call an operation. The legacy KB host and MCP protocol
are separate surfaces. Canonical knowledge routes on MangroveAI remain in the
registered REST contract.

The pinned REST contract declares a default page size of 25 for four on-chain
query bodies and four strategy-workflow request bodies. These defaults apply
when a request omits the field. Existing Python helpers still send their
published explicit page sizes, including 100 on the affected methods, so this
input refresh does not change their behavior. TypeScript's optional request
fields continue to leave the server default in control when omitted.

Canonical workflow bodies use the actual server JSON Schema stored in
`x-mangrove-request-schema`, including canonical authoring unions.
`x-mangrove-raw-json` marks unconstrained serializer values. Opaque response
envelopes remain `unknown` in TypeScript. In particular, some retail Oracle
adapters transform upstream envelopes; their upstream declarations are evidence,
not a false promise that all callers receive that shape.

Generation preserves schema declarations, not live market/account state or
trading policy. Mangrove owns deterministic risk management based on live market
and account conditions; clients submit requests and preserve service decisions.
These fixtures test transport and client contracts. They do not verify that all
execution paths enforce that product responsibility.

## Updating the inputs

1. Export the current backend into a review directory using its
   `scripts/export_developer_contracts.py`. It blocks networking and uses the
   actual application factory without executing business handlers.
2. Run `python3 scripts/generate_typescript_contract.py --check-api-contract-dir
   <export-directory> --check`. A difference identifies drift for review.
3. Review the schema and capability changes. Copy all three reviewed exports and
   their provenance into this directory; keep private upstream source schemas
   in the backend repository.
4. Run `python3 scripts/generate_typescript_contract.py`, inspect the generated
   type and coverage diff, then run the package checks. Regenerate after
   integrating Python SDK changes so its direct-binding inventory is current.
5. Update the backend's committed generation snapshots from the same exports.
   Its source/snapshot test and the SDK input/type check must both pass.

The built wheel and npm tarball must consume the same HTTP fixtures. Tests
should exercise their actual transport, pagination and error handling, rather
than silently restating hand-written response assumptions in isolated models.
Package releases, registry readbacks, consumer adoption and deployed acceptance
are separate from a passing local generation check.

The current declaration includes the three public HelpBot routes even when the
exporter's execution flag is disabled. TypeScript's generic JSON transport
accepts the two JSON operations and rejects the declared SSE operation before
sending a request. Redirect-only declarations are also refused before transport;
JSON successes and opaque JSON declarations remain usable. Python has no dedicated
HelpBot service in its direct-binding inventory. These statements describe client
coverage, not provider activation or live HelpBot acceptance.
