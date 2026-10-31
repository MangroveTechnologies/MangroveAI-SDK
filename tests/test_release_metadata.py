"""Release stamping happens in review; publication verifies the same source bytes."""
from pathlib import Path
from runpy import run_path

import pytest

release = run_path(str(Path(__file__).resolve().parents[1] / "scripts/release_metadata.py"))


def source(tmp_path, project="2.0.0", module="2.0.0"):
    (tmp_path / "src/mangrove_ai").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(f'[project]\nname = "mangroveai"\nversion = "{project}"\n')
    (tmp_path / "src/mangrove_ai/_version.py").write_text(f'__version__ = "{module}"\n')
    return tmp_path


@pytest.mark.parametrize(("bump", "expected"), [("patch", "2.3.5"), ("minor", "2.4.0"), ("major", "3.0.0")])
def test_prepare_changes_both_files_and_verify_never_stamps(tmp_path, bump, expected):
    root = source(tmp_path)
    assert release["next_version"]("v2.3.4", bump) == expected
    release["prepare"](root, expected)
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    release["verify"](root, expected)
    with pytest.raises(ValueError, match="already match"):
        release["verify"](root, "9.0.0")
    assert before == {path: path.read_bytes() for path in before}


def test_disagreement_or_unsafe_version_fails_before_any_source_write(tmp_path):
    root = source(tmp_path, module="2.0.1")
    before = (root / "pyproject.toml").read_bytes()
    with pytest.raises(ValueError, match="disagree"):
        release["prepare"](root, "2.0.2")
    assert (root / "pyproject.toml").read_bytes() == before
    for value in ("v2.0.0", "2.0", "2.0.0-rc1", "2.0.0; echo unsafe", "02.0.0"):
        with pytest.raises(ValueError):
            release["verify"](root, value)
