"""Generate TypeScript declarations and operation metadata from reviewed API contracts."""

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts/mangroveai"
DESTINATION = ROOT / "packages/typescript/src"
METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}


def literal(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def schema_type(schema, namespace, authoring_aliases=None):
    if not isinstance(schema, dict) or not schema:
        return "unknown"
    if schema.get("x-mangrove-raw-json"):
        return "unknown"
    authoring = schema.get("x-mangrove-authoring-schema")
    if isinstance(authoring, dict):
        name = (authoring_aliases or {}).get(authoring.get("$id"))
        normalized = name or schema_type(authoring, namespace, authoring_aliases)
        # Existing HTTP/MCP object acceptance is wider than normalized authoring
        # values. Keep that escape hatch rather than adding client validation.
        return f"({normalized}) | Record<string, unknown>" if authoring.get("$id") else normalized
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1].replace("~1", "/").replace("~0", "~")
        result = f"{namespace}[{literal(name)}]"
    elif "const" in schema:
        result = literal(schema["const"])
    elif "enum" in schema:
        result = " | ".join(literal(item) for item in schema["enum"]) or "never"
    elif "allOf" in schema:
        result = " & ".join("(" + schema_type(item, namespace, authoring_aliases) + ")" for item in schema["allOf"])
    elif "anyOf" in schema or "oneOf" in schema:
        result = " | ".join(
            "(" + schema_type(item, namespace, authoring_aliases) + ")"
            for item in schema.get("anyOf", schema.get("oneOf", []))
        )
    else:
        kind = schema.get("type")
        if isinstance(kind, list):
            return " | ".join(schema_type({**schema, "type": item}, namespace, authoring_aliases) for item in kind)
        if kind == "array":
            result = "Array<" + schema_type(schema.get("items", {}), namespace, authoring_aliases) + ">"
        elif kind == "object" or (kind is None and "properties" in schema):
            required = schema.get("required", [])
            properties = [
                f"{literal(key)}{'' if key in required else '?'}: {schema_type(value, namespace, authoring_aliases)};"
                for key, value in sorted(schema.get("properties", {}).items())
            ]
            extra = schema.get("additionalProperties", True)
            if not properties and isinstance(extra, dict):
                result = "Record<string, " + schema_type(extra, namespace, authoring_aliases) + ">"
            else:
                if isinstance(extra, dict):
                    values = [schema_type(extra, namespace, authoring_aliases)]
                    values.extend(schema_type(value, namespace, authoring_aliases)
                                  for value in schema.get("properties", {}).values())
                    if any(key not in required for key in schema.get("properties", {})):
                        values.append("undefined")
                    properties.append("[key: string]: " + " | ".join(dict.fromkeys(values)) + ";")
                elif extra is not False:
                    properties.append("[key: string]: unknown;")
                result = "{ " + " ".join(properties) + " }"
        else:
            result = {
                "string": "string",
                "integer": "number",
                "number": "number",
                "boolean": "boolean",
                "null": "null",
            }.get(kind, "unknown")
    return "(" + result + ") | null" if schema.get("nullable") or schema.get("x-nullable") else result


def resolve(value, document):
    if "$ref" not in value:
        return value
    result = document
    for part in value["$ref"].removeprefix("#/").split("/"):
        result = result[part.replace("~1", "/").replace("~0", "~")]
    return resolve(result, document)


def python_bindings():
    bindings = {}
    for path in sorted((ROOT / "src/mangrove_ai/_services").rglob("*.py")):
        tree = ast.parse(path.read_text())
        for klass in (item for item in tree.body if isinstance(item, ast.ClassDef)):
            for function in (
                item for item in klass.body if isinstance(item, ast.FunctionDef) and not item.name.startswith("_")
            ):
                for call in ast.walk(function):
                    if not isinstance(call, ast.Call) or len(call.args) < 2 or not isinstance(call.func, ast.Attribute):
                        continue
                    method, uri = call.args[:2]
                    if not isinstance(method, ast.Constant) or method.value not in {item.upper() for item in METHODS}:
                        continue
                    if isinstance(uri, ast.Constant) and isinstance(uri.value, str):
                        route = uri.value
                    elif isinstance(uri, ast.JoinedStr):
                        route = "".join(part.value if isinstance(part, ast.Constant) else "{}" for part in uri.values)
                    else:
                        continue
                    if not route.startswith("/"):
                        continue
                    target = ast.unparse(call.func.value)
                    prefix = "/api/v2" if "v2" in target else "/api/v1"
                    if "/kb/" in str(path):
                        prefix = "legacy-kb-host"
                    key = method.value + " " + re.sub(r"\{[^}]*\}", "{}", prefix + route)
                    bindings.setdefault(key, []).append(f"{klass.name}.{function.name}")
    return bindings


def generate():
    definitions = []
    operations = []
    metadata = {}
    coverage = []
    digests = {}
    python = python_bindings()
    canonical = json.loads((CONTRACTS / "execution-config.schema.json").read_bytes())
    authoring = {canonical["$id"]: canonical}
    aliases = {}
    for filename in ("openapi.json", "oracle-proxy-openapi.json"):
        document = json.loads((CONTRACTS / filename).read_bytes())
        for model in document.get("definitions", document.get("components", {}).get("schemas", {})).values():
            if not isinstance(model, dict):
                continue
            schema = model.get("x-mangrove-authoring-schema", {})
            if not isinstance(schema, dict) or not schema.get("$id"):
                continue
            identity = schema["$id"]
            name = "".join(word[0].upper() + word[1:] for word in re.findall(r"[A-Za-z0-9]+", schema["title"]))
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                raise ValueError("Canonical authoring schema needs a valid type title")
            if identity in authoring and authoring[identity] != schema:
                raise ValueError("Canonical authoring schema differs across API declarations")
            if name in aliases.values() and aliases.get(identity) != name:
                raise ValueError("Canonical authoring type titles collide")
            authoring[identity], aliases[identity] = schema, name
    if canonical["$id"] not in aliases:
        raise ValueError("Canonical execution config is missing from the public API models")
    digests["execution-config.schema.json"] = hashlib.sha256(
        (CONTRACTS / "execution-config.schema.json").read_bytes()
    ).hexdigest()
    for filename, namespace in (("openapi.json", "CoreModels"), ("oracle-proxy-openapi.json", "OracleModels")):
        raw = (CONTRACTS / filename).read_bytes()
        digests[filename] = hashlib.sha256(raw).hexdigest()
        document = json.loads(raw)
        models = document.get("definitions", document.get("components", {}).get("schemas", {}))
        definitions.append(f"export interface {namespace} {{")
        definitions.extend(
            f"  {literal(name)}: {schema_type(schema, namespace, aliases)};" for name, schema in sorted(models.items())
        )
        definitions.append("}\n")
        for path, entry in sorted(document["paths"].items()):
            for method, operation in sorted(entry.items()):
                if method not in METHODS:
                    continue
                key = method.upper() + " " + path
                if key in metadata:
                    raise ValueError(f"Duplicate operation {key}")
                parameters = [
                    resolve(item, document) for item in entry.get("parameters", []) + operation.get("parameters", [])
                ]
                groups = {}
                for location, label in (("path", "path"), ("query", "query"), ("header", "headers")):
                    selected = [
                        item for item in parameters if item.get("in") == location and item["name"].lower() != "x-fields"
                    ]
                    if selected:
                        groups[label] = {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {item["name"]: item.get("schema", item) for item in selected},
                            "required": [item["name"] for item in selected if item.get("required")],
                        }
                # Some legacy declarations omit the path parameter model.
                names = re.findall(r"\{([^}]+)\}", path)
                if names:
                    group = groups.setdefault(
                        "path", {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
                    )
                    for name in names:
                        group["properties"].setdefault(name, {"type": "string"})
                        if name not in group["required"]:
                            group["required"].append(name)
                fields = [
                    f"{name}{'' if group['required'] else '?'}: {schema_type(group, namespace, aliases)};"
                    for name, group in groups.items()
                ]
                body = next((item for item in parameters if item.get("in") == "body"), None)
                request_body = operation.get("requestBody")
                body_schema = body.get("schema", {}) if body else None
                body_required = bool(body and body.get("required"))
                if request_body:
                    media = request_body.get("content", {})
                    body_schema = media.get("application/json", {}).get("schema", {})
                    body_required = bool(request_body.get("required"))
                if "x-mangrove-request-schema" in operation:
                    body_schema = operation["x-mangrove-request-schema"]
                    body_required = bool(body_schema.get("required"))
                if body_schema is not None:
                    body_type = schema_type(body_schema, namespace, aliases)
                    fields.append(f"body{'' if body_required else '?'}: {body_type};")
                response_types = []
                typed_success = False
                response_media = set()
                has_success = False
                for status, value in operation.get("responses", {}).items():
                    if not status.startswith("2"):
                        continue
                    has_success = True
                    value = resolve(value, document)
                    response_media.update(value.get("content", {}))
                    schema = value.get("schema")
                    if schema is None:
                        schema = value.get("content", {}).get("application/json", {}).get("schema")
                    response_types.append(
                        "undefined" if status in {"204", "205"} else schema_type(schema, namespace, aliases)
                    )
                    typed_success = typed_success or bool(schema)
                response = " | ".join(dict.fromkeys(response_types)) or "unknown"
                if "unknown" in response_types:
                    response = "unknown"
                operations.append(f"  {literal(key)}: {{ input: {{ {' '.join(fields)} }}; output: {response}; }};")
                required = {name: group["required"] for name, group in groups.items()}
                metadata[key] = {
                    "method": method.upper(),
                    "path": path,
                    "required": required,
                    "bodyRequired": body_required,
                    "authenticated": bool(operation.get("security", document.get("security", []))),
                    "queryFormats": {
                        item["name"]: item.get(
                            "collectionFormat", "multi" if "schema" in item and item.get("explode", True) else "csv"
                        )
                        for item in parameters
                        if item.get("in") == "query" and item.get("schema", item).get("type") == "array"
                    },
                }
                coverage.append(
                    {
                        "operation": key,
                        "contract": filename,
                        "request": "declared" if body_schema else "no-model-or-no-body",
                        "response": "declared" if typed_success else "opaque-or-no-content",
                        "schema_status": operation.get("x-mangrove-schema-status", "registered-restx-declaration"),
                        "typescript": "request(operation, options)",
                        "runtime_payload_verified": False,
                        "typescript_transport": (
                            "separate-stream-or-non-json-client-required"
                            if response_media
                            and not any(item == "application/json" or item.endswith("+json") for item in response_media)
                            else "separate-redirect-flow-required"
                            if not has_success
                            else "json-or-no-content"
                        ),
                        "python_direct_bindings": sorted(set(python.get(re.sub(r"\{[^}]*\}", "{}", key), []))),
                    }
                )
    source = "// Generated by scripts/generate_typescript_contract.py. Do not edit.\n\n"
    source += "\n".join(f"export type {aliases[identity]} = {schema_type(schema, 'CoreModels')};"
                         for identity, schema in sorted(authoring.items())) + "\n\n"
    source += "\n".join(definitions) + "\nexport interface Operations {\n" + "\n".join(operations) + "\n}\n"
    source += "\nexport type Operation = keyof Operations;\n"
    source += (
        "export const operationMetadata = "
        + json.dumps(metadata, sort_keys=True, ensure_ascii=True, indent=2)
        + " as const;\n"
    )
    report = {
        "contracts": [{"path": name, "sha256": digest} for name, digest in sorted(digests.items())],
        "operations": coverage,
        "python_inventory": (
            "Direct literal/f-string transport bindings only; helpers delegating to another method "
            "are not independent routes. Absence here is not proof that Python cannot call the operation."
        ),
        "limits": (
            "Generated from declarations, not live payload verification. Opaque responses remain unknown. "
            "MCP and the separate legacy KB host are not this REST contract."
        ),
    }
    return {
        DESTINATION / "contract.generated.ts": source,
        CONTRACTS / "coverage.json": json.dumps(report, indent=2, sort_keys=True) + "\n",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--check-api-contract-dir",
        type=Path,
        help="Compare pinned inputs with an offline export from the current backend source",
    )
    args = parser.parse_args()
    provenance = json.loads((CONTRACTS / "provenance.json").read_text())
    expected = {entry["path"]: entry["sha256"] for entry in provenance.get("contracts", [])}
    for name in ("openapi.json", "oracle-proxy-openapi.json", "execution-config.schema.json"):
        raw = (CONTRACTS / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected.get(name):
            raise SystemExit(f"Contract provenance mismatch: {name}")
        if args.check_api_contract_dir and (args.check_api_contract_dir / name).read_bytes() != raw:
            raise SystemExit(f"Backend contract drift: {name} differs from the reviewed SDK input")
    for destination, contents in generate().items():
        if args.check:
            if not destination.exists() or destination.read_text() != contents:
                raise SystemExit(f"Contract drift: regenerate {destination.relative_to(ROOT)}")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(contents)
    print("TypeScript contract matches" if args.check else "TypeScript contract generated")


if __name__ == "__main__":
    main()
