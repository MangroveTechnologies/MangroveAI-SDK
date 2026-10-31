"""The canonical authoring contract is exposed without automatic paid fetches or validation."""
from __future__ import annotations

import copy
import json
import runpy
from pathlib import Path

import httpx
import pytest

from mangrove_ai import MangroveAI
from mangrove_ai.models.config import ExecutionConfigSchema

ROOT = Path(__file__).parents[1]
FIXTURE = json.loads((ROOT / "contracts/mangroveai/fixtures/execution-config-success.json").read_text())


def test_python_reads_canonical_schema_and_nested_glossary_in_one_explicit_call():
    calls = []
    key = "prod_" + "schema-fixture" * 2

    def receive(request):
        calls.append(request)
        assert request.method == "GET"
        assert request.url.path == "/api/v1/config/execution-config-schema"
        assert request.headers["Authorization"] == f"Bearer {key}"
        return httpx.Response(200, json=FIXTURE)

    with MangroveAI(
        api_key=key, environment="prod", base_url="https://schema.fixture.invalid/api/v1",
        load_dotenv=False, auto_auth=False, auto_retry=False,
        httpx_client=httpx.Client(transport=httpx.MockTransport(receive)),
    ) as client:
        assert not calls
        result = client.config.get_execution_config_schema()
    assert len(calls) == 1
    assert result.json_schema == FIXTURE["json_schema"]
    assert result.defaults == FIXTURE["defaults"]
    metadata = result.param_glossary["cooldown_config"]
    assert metadata.required_fields == FIXTURE["param_glossary"]["cooldown_config"]["required_fields"]
    assert metadata.fields is not None
    assert metadata.fields["short_window_bars"].type == "int"
    assert metadata.metadata_fields is not None
    assert metadata.metadata_fields["cadence_reference"].type == "str"


def test_older_receiver_without_additive_schema_or_nested_metadata_still_parses():
    old = copy.deepcopy(FIXTURE)
    old.pop("json_schema")
    old["param_glossary"]["cooldown_config"].pop("fields")
    old["param_glossary"]["cooldown_config"].pop("required_fields")
    old["param_glossary"]["cooldown_config"].pop("metadata_fields")
    result = ExecutionConfigSchema.model_validate(old)
    assert result.json_schema is None
    assert result.param_glossary["cooldown_config"].fields is None


def test_generated_type_uses_canonical_fields_with_a_legacy_transport_escape_hatch():
    generator = runpy.run_path(str(ROOT / "scripts/generate_typescript_contract.py"))
    schema_type = generator["schema_type"]
    document = json.loads((ROOT / "contracts/mangroveai/openapi.json").read_text())
    canonical = json.loads((ROOT / "contracts/mangroveai/execution-config.schema.json").read_text())
    model = document["definitions"]["api1.ExecutionConfiguration"]
    assert not model.get("x-mangrove-raw-json")
    assert model["x-mangrove-authoring-schema"] == canonical
    assert schema_type(model, "CoreModels", {canonical["$id"]: "ExecutionConfiguration"}) == (
        "(ExecutionConfiguration) | Record<string, unknown>"
    )
    normalized = schema_type(canonical, "CoreModels")
    assert '"max_risk_per_trade"?: number | null;' in normalized
    assert '"short_window_bars": number;' in normalized
    assert '"short_cooldown_bars"?: number;' in normalized
    assert normalized != "unknown"


@pytest.mark.parametrize("metadata", [False, {"type": "integer"}])
def test_unconstrained_raw_values_are_still_opaque(metadata):
    schema_type = runpy.run_path(str(ROOT / "scripts/generate_typescript_contract.py"))["schema_type"]
    assert schema_type({"x-mangrove-raw-json": True, "type": "object", "additionalProperties": metadata}, "Models") == "unknown"
