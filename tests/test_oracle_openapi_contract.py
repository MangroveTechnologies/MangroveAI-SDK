"""Regression guard against Oracle OpenAPI and SDK data-query model drift."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

import scripts.check_oracle_openapi_contract as contract_check
from scripts.check_oracle_openapi_contract import (
    ContractDriftError,
    _assert_schema_compatible,
    check_data_query_contract,
    load_contract_snapshot,
)


@pytest.fixture
def oracle_openapi() -> dict:
    # Missing snapshots fail the test rather than silently disabling the guard.
    return load_contract_snapshot()


def test_sdk_data_query_models_match_generated_oracle_openapi(oracle_openapi: dict) -> None:
    check_data_query_contract(oracle_openapi)


def test_contract_snapshot_fails_closed_when_missing_or_unprovenanced(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schema_path = tmp_path / "oracle-openapi.json"
    provenance_path = tmp_path / "oracle-openapi-provenance.json"
    monkeypatch.setattr(contract_check, "CONTRACT_PATH", schema_path)
    monkeypatch.setattr(contract_check, "PROVENANCE_PATH", provenance_path)

    with pytest.raises(ContractDriftError, match="snapshot is missing"):
        contract_check.load_contract_snapshot()

    schema_bytes = b'{"openapi":"3.1.0"}\n'
    schema_path.write_bytes(schema_bytes)
    provenance_path.write_text(json.dumps({
        "source_repository": "MangroveTechnologies/MangroveOracle",
        "source_commit": "source-revision",
        "schema_sha256": hashlib.sha256(b"stale schema").hexdigest(),
    }))
    with pytest.raises(ContractDriftError, match="hash does not match"):
        contract_check.load_contract_snapshot()


def test_contract_check_detects_required_request_field_drift(oracle_openapi: dict) -> None:
    changed = copy.deepcopy(oracle_openapi)
    changed["components"]["schemas"]["QueryRequest"]["required"].remove("select")

    with pytest.raises(ContractDriftError, match="required request fields differ"):
        check_data_query_contract(changed)


def test_contract_check_detects_response_nullability_drift(oracle_openapi: dict) -> None:
    changed = copy.deepcopy(oracle_openapi)
    changed["components"]["schemas"]["QueryResponse"]["properties"]["row_count"] = {
        "anyOf": [{"type": "integer"}, {"type": "null"}]
    }

    with pytest.raises(ContractDriftError, match="row_count.*incompatible"):
        check_data_query_contract(changed)


def test_contract_check_detects_response_type_drift(oracle_openapi: dict) -> None:
    changed = copy.deepcopy(oracle_openapi)
    changed["components"]["schemas"]["QueryResponse"]["properties"]["row_count"] = {
        "type": "string"
    }

    with pytest.raises(ContractDriftError, match="row_count.*incompatible"):
        check_data_query_contract(changed)


def test_contract_check_detects_wire_alias_drift(oracle_openapi: dict) -> None:
    changed = copy.deepcopy(oracle_openapi)
    properties = changed["components"]["schemas"]["QueryRequest"]["properties"]
    properties["orderBy"] = properties.pop("order_by")

    with pytest.raises(ContractDriftError, match="request wire fields differ"):
        check_data_query_contract(changed)


def test_contract_check_detects_nested_request_default_drift(oracle_openapi: dict) -> None:
    changed = copy.deepcopy(oracle_openapi)
    changed["components"]["schemas"]["OrderBy"]["properties"]["dir"]["default"] = "desc"

    with pytest.raises(ContractDriftError, match="dir.*differs from Oracle default"):
        check_data_query_contract(changed)


def test_contract_check_detects_nullable_nested_reference_drift(oracle_openapi: dict) -> None:
    server = {
        "components": {"schemas": {"OrderBy": {
            "type": "object",
            "properties": {"dir": {"anyOf": [{"type": "string"}, {"type": "null"}]}},
        }}}
    }
    sdk = {"$defs": {"OrderBy": {"type": "object", "properties": {"dir": {"type": "string"}}}}}

    with pytest.raises(ContractDriftError, match="order_by.dir.*incompatible"):
        _assert_schema_compatible(
            {"$ref": "#/components/schemas/OrderBy"},
            {"$ref": "#/$defs/OrderBy"},
            server,
            sdk,
            direction="response",
            path="order_by",
        )


def test_nullable_reference_still_checks_nested_properties_and_defaults() -> None:
    server_order = {
        "type": "object",
        "properties": {"dir": {"type": "string", "default": "desc"}},
    }
    server = {
        "components": {"schemas": {
            "OrderBy": server_order,
            "NullableOrderBy": {"anyOf": [
                {"$ref": "#/components/schemas/OrderBy"}, {"type": "null"}
            ]},
        }}
    }
    sdk = {"$defs": {"OrderBy": {
        "type": "object",
        "properties": {"dir": {"type": "string", "default": "asc"}},
    }}}

    with pytest.raises(ContractDriftError, match="dir.*differs from Oracle default"):
        _assert_schema_compatible(
            {"$ref": "#/components/schemas/NullableOrderBy"},
            {"$ref": "#/$defs/OrderBy"},
            server,
            sdk,
            direction="request",
            path="order_by",
        )


def test_contract_check_detects_array_item_type_drift(oracle_openapi: dict) -> None:
    changed = copy.deepcopy(oracle_openapi)
    changed["components"]["schemas"]["QueryRequest"]["properties"]["select"]["items"]["type"] = "integer"

    with pytest.raises(ContractDriftError, match=r"select\[\].*incompatible"):
        check_data_query_contract(changed)


def test_unconstrained_values_are_not_treated_as_empty_type_sets() -> None:
    with pytest.raises(ContractDriftError, match="incompatible"):
        _assert_schema_compatible({"type": "integer"}, {}, {}, {}, direction="request", path="value")
    with pytest.raises(ContractDriftError, match="incompatible"):
        _assert_schema_compatible({}, {"type": "integer"}, {}, {}, direction="response", path="value")

    _assert_schema_compatible({}, {}, {}, {}, direction="request", path="value")
    _assert_schema_compatible({}, {}, {}, {}, direction="response", path="value")


def test_unsupported_schema_composition_fails_closed() -> None:
    with pytest.raises(ContractDriftError, match="unsupported JSON Schema keywords"):
        _assert_schema_compatible(
            {"allOf": [{"type": "string"}]},
            {"type": "string"},
            {},
            {},
            direction="response",
            path="value",
        )

    with pytest.raises(ContractDriftError, match=r"structural keywords beside \$ref"):
        _assert_schema_compatible(
            {"$ref": "#/components/schemas/Value", "type": "string"},
            {"type": "string"},
            {"components": {"schemas": {"Value": {"type": "string"}}}},
            {},
            direction="response",
            path="value",
        )


def test_additional_property_schemas_are_checked_directionally() -> None:
    with pytest.raises(ContractDriftError, match="additional properties Oracle constrains"):
        _assert_schema_compatible(
            {"type": "object", "additionalProperties": {"type": "integer"}},
            {"type": "object", "additionalProperties": True},
            {},
            {},
            direction="request",
            path="payload",
        )
    with pytest.raises(ContractDriftError, match=r"payload\.\*.*incompatible"):
        _assert_schema_compatible(
            {"type": "object", "additionalProperties": {"type": "integer"}},
            {"type": "object", "additionalProperties": {"type": "string"}},
            {},
            {},
            direction="response",
            path="payload",
        )


def test_response_sdk_may_accept_wider_types_enums_and_bounds() -> None:
    _assert_schema_compatible(
        {"type": "integer", "maximum": 10},
        {"type": "integer"},
        {},
        {},
        direction="response",
        path="row_count",
    )
    _assert_schema_compatible(
        {"type": "string", "enum": ["known"]},
        {"type": "string"},
        {},
        {},
        direction="response",
        path="status",
    )
