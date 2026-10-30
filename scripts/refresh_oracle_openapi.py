#!/usr/bin/env python3
"""Refresh the reviewed Oracle OpenAPI snapshot from an Oracle source checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "contracts" / "oracle-openapi.json"
PROVENANCE_PATH = REPO_ROOT / "contracts" / "oracle-openapi-provenance.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oracle-source", type=Path, required=True, help="Oracle source checkout")
    parser.add_argument(
        "--mangroveai-source", type=Path, required=True,
        help="MangroveAI source checkout for Oracle's canon import",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="regenerate in memory and fail if the reviewed snapshot or provenance is stale",
    )
    args = parser.parse_args()
    oracle_source = args.oracle_source.resolve()
    ai_source = args.mangroveai_source.resolve()
    for source in (oracle_source, ai_source):
        if not source.is_dir():
            parser.error(f"source directory does not exist: {source}")

    def source_revision(path: Path) -> tuple[str, bool]:
        commit = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip())
        return commit, dirty

    oracle_commit, oracle_dirty = source_revision(oracle_source)
    ai_commit, ai_dirty = source_revision(ai_source)
    if oracle_dirty or ai_dirty:
        raise SystemExit(
            "refusing to export a schema from dirty source checkouts; "
            f"Oracle dirty={oracle_dirty}, MangroveAI dirty={ai_dirty}"
        )

    # Oracle imports the packaged canon with ``find_spec("MangroveAI")``;
    # the source checkout's import root is its ``src`` directory.
    python_path = os.pathsep.join((str(oracle_source), str(ai_source / "src")))
    env = {**os.environ, "PYTHONPATH": python_path}
    generate = (
        "import json; from src.app import app; "
        "print(json.dumps(app.openapi(), sort_keys=True, indent=2))"
    )
    rendered = subprocess.run(
        [sys.executable, "-c", generate],
        cwd=oracle_source,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    spec = json.loads(rendered)
    schema_bytes = (json.dumps(spec, sort_keys=True, indent=2) + "\n").encode()
    provenance = {
        "source_repository": "MangroveTechnologies/MangroveOracle",
        "source_commit": oracle_commit,
        "source_dirty": oracle_dirty,
        "mangroveai_source_repository": "MangroveTechnologies/MangroveAI",
        "mangroveai_source_commit": ai_commit,
        "mangroveai_source_dirty": ai_dirty,
        "openapi_version": spec.get("openapi"),
        "api_title": spec.get("info", {}).get("title"),
        "api_version": spec.get("info", {}).get("version"),
        "schema_sha256": hashlib.sha256(schema_bytes).hexdigest(),
        "generation": "src.app.app.openapi() with lifespan not started",
    }
    provenance_bytes = (json.dumps(provenance, indent=2) + "\n").encode()
    if args.check:
        try:
            current_schema = SCHEMA_PATH.read_bytes()
            current_provenance = PROVENANCE_PATH.read_bytes()
        except FileNotFoundError as exc:
            print(f"contract snapshot is incomplete: {exc.filename}", file=sys.stderr)
            return 1
        if current_schema != schema_bytes or current_provenance != provenance_bytes:
            print("Oracle OpenAPI snapshot is stale for the supplied source revisions", file=sys.stderr)
            return 1
        print(f"Oracle OpenAPI snapshot matches Oracle {oracle_commit} and MangroveAI {ai_commit}")
        return 0

    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_bytes(schema_bytes)
    PROVENANCE_PATH.write_bytes(provenance_bytes)
    print(f"Wrote {SCHEMA_PATH.relative_to(REPO_ROOT)} from Oracle {oracle_commit}")
    print(f"Wrote {PROVENANCE_PATH.relative_to(REPO_ROOT)} (MangroveAI {ai_commit})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
