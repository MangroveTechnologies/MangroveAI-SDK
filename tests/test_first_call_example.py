"""The public first-call script uses the real SDK with intercepted HTTP."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import httpx
import pytest

from mangrove_ai import MangroveAI


@pytest.mark.parametrize("status", [200, 401, 402, 403, 429, 503])
def test_example_reads_private_config_without_echoing_key(tmp_path, monkeypatch, capsys, status):
    path = Path(__file__).parents[1] / "examples" / "first_call.py"
    spec = importlib.util.spec_from_file_location("first_call_example", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    key = "prod_example_fixture_not_a_real_key"
    config = tmp_path / "private-config.json"
    config.write_text(json.dumps({"api_key": key}))
    seen = []

    def handler(request):
        seen.append(request)
        assert request.url.path == "/api/v1/users/me/metrics"
        assert request.headers["Authorization"] == f"Bearer {key}"
        assert request.extensions["timeout"]["read"] == 15
        return httpx.Response(status, json={
            "success": status == 200, "metrics": {"messages_count": 4},
            "error": "fixture", "message": key,
        })

    def fixture_client(**kwargs):
        assert kwargs["load_dotenv"] is False
        assert kwargs["auto_retry"] is False
        return MangroveAI(**kwargs, httpx_client=httpx.Client(transport=httpx.MockTransport(handler)))

    monkeypatch.setattr(module, "MangroveAI", fixture_client)
    monkeypatch.setattr(sys, "argv", [str(path), str(config)])
    assert module.main() == (0 if status == 200 else 1)
    output = capsys.readouterr().out
    assert key not in output
    result = json.loads(output)
    assert result["status"] == ("ok" if status == 200 else "api_error")
    if status == 200:
        assert result["metrics"]["messages_count"] == 4
    else:
        assert result["http_status"] == status
    assert len(seen) == 1
