#!/usr/bin/env python3
"""Check the SDK data-query wire models against a reviewed Oracle OpenAPI snapshot."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "contracts" / "oracle-openapi.json"
PROVENANCE_PATH = REPO_ROOT / "contracts" / "oracle-openapi-provenance.json"
_SUPPORTED_SCHEMA_KEYS = {
    "$defs", "$ref", "additionalProperties", "anyOf", "const", "default", "description", "enum",
    "items", "maxItems", "maximum", "minItems", "minimum", "properties", "required",
    "title", "type",
}
sys.path.insert(0, str(REPO_ROOT / "src"))


class ContractDriftError(AssertionError):
    """The Oracle schema and SDK wire models no longer agree."""


def load_contract_snapshot() -> dict[str, Any]:
    if not CONTRACT_PATH.is_file():
        raise ContractDriftError(f"Oracle OpenAPI contract snapshot is missing: {CONTRACT_PATH}")
    if not PROVENANCE_PATH.is_file():
        raise ContractDriftError(f"Oracle OpenAPI provenance is missing: {PROVENANCE_PATH}")
    schema_bytes = CONTRACT_PATH.read_bytes()
    provenance = json.loads(PROVENANCE_PATH.read_text())
    actual_hash = hashlib.sha256(schema_bytes).hexdigest()
    if provenance.get("schema_sha256") != actual_hash:
        raise ContractDriftError("Oracle OpenAPI snapshot hash does not match its provenance")
    if (
        not provenance.get("source_commit")
        or provenance.get("source_dirty") is not False
        or provenance.get("source_repository") != "MangroveTechnologies/MangroveOracle"
        or not provenance.get("mangroveai_source_commit")
        or provenance.get("mangroveai_source_dirty") is not False
        or provenance.get("mangroveai_source_repository") != "MangroveTechnologies/MangroveAI"
    ):
        raise ContractDriftError("Oracle OpenAPI provenance is missing its authoritative source revision")
    return json.loads(schema_bytes)


def _resolve_ref(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if ref is None:
        return schema
    siblings = set(schema) - {"$ref", "title", "description"}
    if siblings:
        raise ContractDriftError(f"structural keywords beside $ref are unsupported: {sorted(siblings)}")
    if not ref.startswith("#/"):
        raise ContractDriftError(f"unsupported schema reference: {ref}")
    value: Any = root
    for part in ref[2:].split("/"):
        value = value[part]
    return _resolve_ref(value, root)


def _accepted_types(schema: dict[str, Any], root: dict[str, Any]) -> set[str]:
    schema = _resolve_ref(schema, root)
    unsupported = set(schema) - _SUPPORTED_SCHEMA_KEYS
    if unsupported:
        raise ContractDriftError(f"unsupported JSON Schema keywords: {sorted(unsupported)}")
    if "type" in schema:
        if "anyOf" in schema or "oneOf" in schema:
            raise ContractDriftError("combined type and union schema is unsupported")
        return {schema["type"]} if isinstance(schema["type"], str) else set(schema["type"])
    variants = schema.get("anyOf", schema.get("oneOf", []))
    if not variants:
        # A title/description-only schema is a true unconstrained value (used
        # for the DSL's arbitrary filter value), not an empty set of types.
        return set()
    if len(variants) != 2 or sum(_accepted_types(part, root) == {"null"} for part in variants) != 1:
        raise ContractDriftError("only a single nullable JSON Schema variant is supported")
    return set().union(*(_accepted_types(part, root) for part in variants))


def _without_null_variant(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    variants = schema.get("anyOf", schema.get("oneOf"))
    if not variants:
        return schema
    non_null = [part for part in variants if _accepted_types(part, root) != {"null"}]
    return _resolve_ref(non_null[0], root) if len(non_null) == 1 else schema


def _assert_schema_compatible(
    server_schema: dict[str, Any],
    sdk_schema: dict[str, Any],
    server_root: dict[str, Any],
    sdk_root: dict[str, Any],
    *,
    direction: str,
    path: str,
    sdk_field_optional: bool = False,
) -> None:
    server_schema = _resolve_ref(server_schema, server_root)
    sdk_schema = _resolve_ref(sdk_schema, sdk_root)

    server_types = _accepted_types(server_schema, server_root)
    sdk_types = _accepted_types(sdk_schema, sdk_root)
    # SDK query() serializes request models with exclude_none=True. An optional
    # request field whose default is None is omitted on the wire, not sent as null.
    if direction == "request" and sdk_field_optional and sdk_schema.get("default", object()) is None:
        sdk_types.discard("null")
        sdk_schema = _without_null_variant(sdk_schema, sdk_root)
    if direction == "request":
        # An unconstrained SDK request can emit values a typed server rejects;
        # a typed SDK can safely send to an unconstrained server.
        compatible_types = not server_types if not sdk_types else not server_types or sdk_types.issubset(server_types)
    else:
        # An unconstrained server response requires an unconstrained SDK field;
        # an unconstrained SDK field can safely parse typed server output.
        compatible_types = not sdk_types if not server_types else not sdk_types or server_types.issubset(sdk_types)
    if not compatible_types:
        raise ContractDriftError(
            f"{path}: SDK types {sorted(sdk_types)} are incompatible with Oracle types "
            f"{sorted(server_types)} ({direction})"
        )

    # The nullability check above preserves nullable behavior. Compare the
    # non-null branch separately so array items and nested object constraints
    # are not lost when walking a nullable union.
    server_schema = _without_null_variant(server_schema, server_root)
    sdk_schema = _without_null_variant(sdk_schema, sdk_root)

    server_enum = server_schema.get("enum")
    sdk_enum = sdk_schema.get("enum")
    if server_enum is not None:
        values_fit = (
            sdk_enum is not None and set(sdk_enum).issubset(server_enum)
            if direction == "request"
            else sdk_enum is None or set(server_enum).issubset(sdk_enum)
        )
        if not values_fit:
            raise ContractDriftError(f"{path}: SDK enum {sdk_enum} does not cover Oracle enum {server_enum}")
    elif direction == "response" and sdk_enum is not None:
        raise ContractDriftError(f"{path}: Oracle has no enum but SDK response only accepts {sdk_enum}")
    if "const" in server_schema:
        if direction == "request" and sdk_schema.get("const") != server_schema["const"]:
            raise ContractDriftError(f"{path}: SDK const does not match Oracle const {server_schema['const']!r}")
        if direction == "response" and sdk_schema.get("const", server_schema["const"]) != server_schema["const"]:
            raise ContractDriftError(
                f"{path}: SDK response const does not accept Oracle const {server_schema['const']!r}"
            )
    elif direction == "response" and "const" in sdk_schema:
        raise ContractDriftError(f"{path}: SDK response is narrower than Oracle's unconstrained field")

    server_properties = server_schema.get("properties", {})
    sdk_properties = sdk_schema.get("properties", {})
    if server_properties or sdk_properties:
        if direction == "request":
            if set(server_properties) != set(sdk_properties):
                raise ContractDriftError(
                    f"{path}: request wire fields differ; Oracle={sorted(server_properties)}, "
                    f"SDK={sorted(sdk_properties)}"
                )
        elif not set(server_properties).issubset(sdk_properties):
            raise ContractDriftError(
                f"{path}: SDK is missing Oracle response fields "
                f"{sorted(set(server_properties) - set(sdk_properties))}"
            )

        server_required = set(server_schema.get("required", []))
        sdk_required = set(sdk_schema.get("required", []))
        if direction == "request" and server_required != sdk_required:
            raise ContractDriftError(
                f"{path}: required request fields differ; Oracle={sorted(server_required)}, "
                f"SDK={sorted(sdk_required)}"
            )
        if direction == "response" and not sdk_required.issubset(server_required):
            raise ContractDriftError(
                f"{path}: SDK requires response fields Oracle may omit: "
                f"{sorted(sdk_required - server_required)}"
            )

        for name in set(server_properties).intersection(sdk_properties):
            _assert_schema_compatible(
                server_properties[name],
                sdk_properties[name],
                server_root,
                sdk_root,
                direction=direction,
                path=f"{path}.{name}",
                sdk_field_optional=name not in sdk_required,
            )

    if "items" in server_schema or "items" in sdk_schema:
        if "items" not in server_schema or "items" not in sdk_schema:
            raise ContractDriftError(f"{path}: Oracle and SDK array item schemas differ")
        _assert_schema_compatible(
            server_schema["items"], sdk_schema["items"], server_root, sdk_root,
            direction=direction, path=f"{path}[]",
        )

    server_additional = server_schema.get("additionalProperties", True)
    sdk_additional = sdk_schema.get("additionalProperties", True)
    if direction == "request":
        if server_additional is False and sdk_additional is not False:
            raise ContractDriftError(f"{path}: SDK may send additional properties Oracle rejects")
        if isinstance(server_additional, dict) and sdk_additional is True:
            raise ContractDriftError(f"{path}: SDK allows unconstrained additional properties Oracle constrains")
    else:
        if server_additional is True and sdk_additional is not True:
            raise ContractDriftError(f"{path}: SDK rejects additional properties Oracle may return")
        if isinstance(server_additional, dict) and sdk_additional is False:
            raise ContractDriftError(f"{path}: SDK rejects additional properties Oracle may return")
    if isinstance(server_additional, dict) and isinstance(sdk_additional, dict):
        _assert_schema_compatible(
            server_additional, sdk_additional, server_root, sdk_root,
            direction=direction, path=f"{path}.*",
        )

    for bound in ("minItems", "maxItems", "minimum", "maximum"):
        server_bound = server_schema.get(bound)
        sdk_bound = sdk_schema.get(bound)
        if server_bound is None and sdk_bound is None:
            continue
        if sdk_bound is None:
            if direction == "response":
                continue
            raise ContractDriftError(f"{path}: SDK omits Oracle {bound}={server_bound}")
        if server_bound is None:
            if direction == "request":
                continue
            raise ContractDriftError(f"{path}: SDK {bound}={sdk_bound} narrows Oracle's unbounded response")
        if bound.startswith("min") or bound == "minimum":
            fits = sdk_bound >= server_bound if direction == "request" else sdk_bound <= server_bound
        else:
            fits = sdk_bound <= server_bound if direction == "request" else sdk_bound >= server_bound
        if not fits:
            raise ContractDriftError(f"{path}: SDK {bound}={sdk_bound} conflicts with Oracle {bound}={server_bound}")

    if direction == "request" and "default" in server_schema and "default" in sdk_schema:
        if server_schema["default"] != sdk_schema["default"]:
            raise ContractDriftError(
                f"{path}: SDK default {sdk_schema['default']!r} differs from Oracle default "
                f"{server_schema['default']!r}"
            )


def check_data_query_contract(spec: dict[str, Any]) -> None:
    """Check Oracle's actual data-query operation against the SDK's wire models."""
    from mangrove_ai.models.oracle import DataQueryRequest, DataQueryResponse

    path = spec.get("paths", {}).get("/api/v1/data/query", {}).get("post")
    if not path:
        raise ContractDriftError("Oracle OpenAPI is missing POST /api/v1/data/query")
    request_ref = path.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
    response_ref = path.get("responses", {}).get("200", {}).get("content", {}).get("application/json", {}).get("schema")
    if not request_ref or not response_ref:
        raise ContractDriftError("Oracle data-query operation is missing JSON request/200 response schemas")

    sdk_request = DataQueryRequest.model_json_schema(by_alias=True)
    sdk_response = DataQueryResponse.model_json_schema(by_alias=True)
    _assert_schema_compatible(
        request_ref, sdk_request, spec, sdk_request, direction="request", path="data_query.request"
    )
    _assert_schema_compatible(
        response_ref, sdk_response, spec, sdk_response, direction="response", path="data_query.response"
    )


def main() -> int:
    try:
        spec = load_contract_snapshot()
        check_data_query_contract(spec)
    except (ContractDriftError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"Oracle OpenAPI contract check failed: {exc}", file=sys.stderr)
        return 1
    print("Oracle POST /api/v1/data/query matches the SDK request and response models")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
