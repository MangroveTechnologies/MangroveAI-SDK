"""The Cambrian demo skips unavailable signals before requesting their details."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import httpx
import pytest

from mangrove_ai import MangroveAI


@pytest.mark.parametrize("availability", [
    None, {"composable": False, "status": "disabled"}, {},
    {"composable": None}, {"status": "disabled"},
    {"composable": True, "status": "disabled"},
], ids=["missing", "non_composable", "unspecified", "null", "status_only", "contradictory"])
def test_demo_skips_unavailable_exit_without_detail_or_strategy_requests(monkeypatch, capsys, availability):
    path = Path(__file__).parents[1] / "examples" / "cambrian_signals_demo.py"
    spec = importlib.util.spec_from_file_location("cambrian_example", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    requests = []

    def handler(request):
        requests.append(request)
        if request.method != "GET" or request.url.path != "/api/v1/signals/":
            return httpx.Response(404, json={"error": "Signal not available"})
        signals = [{
            "name": "social_price_divergence",
            "category": "social",
            "signal_type": "TRIGGER",
            **(availability or {}),
            "reason": "Data source unavailable",
        }] if availability is not None and request.url.params.get("category") == "social" else []
        return httpx.Response(200, json={"signals": signals, "total": len(signals), "limit": 50, "offset": 0})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = MangroveAI(
        api_key="test_fixture_not_a_real_key", environment="local", load_dotenv=False,
        auto_retry=False, httpx_client=http_client,
    )
    monkeypatch.setenv("MANGROVE_API_KEY", "test_fixture_not_a_real_key")
    monkeypatch.setattr(module, "MangroveAI", lambda: client)

    module.main()

    assert "Skipping the strategy: social_price_divergence is missing or non-composable" in capsys.readouterr().out
    assert [(r.method, r.url.path, r.url.params.get("category")) for r in requests] == [
        ("GET", "/api/v1/signals/", "social"),
        ("GET", "/api/v1/signals/", "onchain"),
    ]
    assert http_client.is_closed
