"""Tests for .env autoloading and API-key resolution precedence.

Covers issue #36: the SDK should optionally load a `.env` file (via the
`python-dotenv` soft dependency) while keeping real process env vars authoritative.
"""
from __future__ import annotations

import os
import sys

import pytest

from mangrove_ai import MangroveAI
from mangrove_ai._config import ClientConfig


@pytest.fixture(autouse=True)
def _restore_environ():
    """Snapshot and restore os.environ — load_dotenv mutates it directly."""
    saved = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(saved)


def _write_env(dir_path, body: str) -> None:
    (dir_path / ".env").write_text(body)


class TestDotenvAutoload:
    """python-dotenv is installed in the dev env, so autoload is active."""

    def test_loads_api_key_from_dotenv(self, tmp_path, monkeypatch) -> None:
        monkeypatch.delenv("MANGROVE_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)
        _write_env(tmp_path, "MANGROVE_API_KEY=prod_from_dotenv\n")

        config = ClientConfig()

        assert config.api_key == "prod_from_dotenv"

    def test_client_picks_up_dotenv_key_with_no_args(self, tmp_path, monkeypatch) -> None:
        monkeypatch.delenv("MANGROVE_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)
        _write_env(tmp_path, "MANGROVE_API_KEY=prod_from_dotenv\n")

        client = MangroveAI()  # the exact call the README documents

        assert client._config.api_key == "prod_from_dotenv"

    def test_process_env_wins_over_dotenv(self, tmp_path, monkeypatch) -> None:
        """Real env vars must take precedence — override=False."""
        monkeypatch.setenv("MANGROVE_API_KEY", "prod_from_real_env")
        monkeypatch.chdir(tmp_path)
        _write_env(tmp_path, "MANGROVE_API_KEY=prod_from_dotenv\n")

        config = ClientConfig()

        assert config.api_key == "prod_from_real_env"

    def test_explicit_arg_wins_over_dotenv(self, tmp_path, monkeypatch) -> None:
        monkeypatch.delenv("MANGROVE_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)
        _write_env(tmp_path, "MANGROVE_API_KEY=prod_from_dotenv\n")

        config = ClientConfig(api_key="prod_explicit")

        assert config.api_key == "prod_explicit"

    def test_load_dotenv_false_disables_autoload(self, tmp_path, monkeypatch) -> None:
        monkeypatch.delenv("MANGROVE_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)
        _write_env(tmp_path, "MANGROVE_API_KEY=prod_from_dotenv\n")

        config = ClientConfig(load_dotenv=False)

        assert config.api_key is None


class TestSoftDependency:
    """When python-dotenv is absent, the SDK reads os.environ only (no crash)."""

    def test_missing_dotenv_is_a_noop(self, tmp_path, monkeypatch) -> None:
        # Simulate python-dotenv not being installed.
        monkeypatch.setitem(sys.modules, "dotenv", None)
        monkeypatch.delenv("MANGROVE_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)
        _write_env(tmp_path, "MANGROVE_API_KEY=prod_from_dotenv\n")

        # Must not raise; .env is simply ignored.
        config = ClientConfig()

        assert config.api_key is None

    def test_missing_dotenv_still_reads_real_env(self, monkeypatch) -> None:
        monkeypatch.setitem(sys.modules, "dotenv", None)
        monkeypatch.setenv("MANGROVE_API_KEY", "prod_from_real_env")

        config = ClientConfig()

        assert config.api_key == "prod_from_real_env"
