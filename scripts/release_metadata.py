"""Prepare reviewed version changes or verify an unchanged release source tree."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
FILES = (("pyproject.toml", "version"), ("src/mangrove_ai/_version.py", "__version__"))


def checked_version(value: str) -> str:
    if not VERSION.fullmatch(value):
        raise ValueError("Expected a stable numeric major.minor.patch version.")
    return value


def next_version(previous: str, bump: str) -> str:
    parts = [int(part) for part in checked_version(previous.removeprefix("v")).split(".")]
    index = {"major": 0, "minor": 1, "patch": 2}[bump]
    parts[index] += 1
    parts[index + 1:] = [0] * (2 - index)
    return ".".join(map(str, parts))


def source_versions(root: Path) -> list[str]:
    versions = []
    for filename, variable in FILES:
        matches = re.findall(rf'^{variable} = "([^"]+)"$', (root / filename).read_text(), re.MULTILINE)
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one {variable} assignment in {filename}.")
        versions.append(checked_version(matches[0]))
    return versions


def prepare(root: Path, version: str) -> None:
    checked_version(version)
    versions = source_versions(root)
    if len(set(versions)) != 1:
        raise ValueError("Version files disagree; reconcile before preparing a release.")
    for filename, variable in FILES:
        path = root / filename
        path.write_text(re.sub(rf'^{variable} = "[^"]+"$', f'{variable} = "{version}"',
                               path.read_text(), flags=re.MULTILINE))


def verify(root: Path, version: str) -> None:
    checked_version(version)
    if source_versions(root) != [version, version]:
        raise ValueError("Release version must already match both version files in reviewed main source.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    stamp = commands.add_parser("prepare")
    stamp.add_argument("--previous", required=True)
    stamp.add_argument("--bump", choices=("patch", "minor", "major"), required=True)
    check = commands.add_parser("verify")
    check.add_argument("--version", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.command == "prepare":
        version = next_version(args.previous, args.bump)
        prepare(root, version)
        print(f"version={version}\ntag=v{version}\nprevious={args.previous}")
    else:
        verify(root, args.version)
        print(f"version={args.version}\ntag=v{args.version}")


if __name__ == "__main__":
    main()
