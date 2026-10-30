# Shared MangroveAI contracts

These are pinned generation inputs and synthetic HTTP fixtures for the Python
and TypeScript clients. `provenance.json` records the backend source commit,
source hashes and exported-document hashes. No real user, API key, session token
or account record belongs here.

`openapi.json` preserves the registered RESTX v1/v2 contract in Swagger 2.0.
`oracle-proxy-openapi.json` uses OpenAPI 3.1 and describes only upstream paths
reachable through the actual MangroveAI proxy allowlist and forwarded methods.
Its servers point at MangroveAI, not private upstream deployment hosts.

`coverage.json` enumerates every generated REST operation, response modelling
status and matching direct Python transport bindings. Python wrappers delegating
to another method are not separate routes; an empty direct-binding list is not
proof that Python cannot call an operation. The legacy KB host and MCP protocol
are separate surfaces. Canonical knowledge routes on MangroveAI remain in the
registered REST contract.

Canonical workflow bodies use the actual server JSON Schema stored in
`x-mangrove-request-schema`, including unions Swagger 2.0 cannot express.
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
3. Review the schema and capability changes. Copy both reviewed exports and
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
