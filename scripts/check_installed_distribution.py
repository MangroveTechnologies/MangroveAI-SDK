"""Offline smoke check for a wheel installed in an isolated environment.

Run with that environment's Python: python -I scripts/check_installed_distribution.py
The fixture intercepts every request; no network or real credential is used.
"""
from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path

import httpx

import mangrove_ai
from mangrove_ai import MalformedResponseError, MangroveAI, PaymentRequiredError


def main() -> None:
    assert "site-packages" in str(Path(mangrove_ai.__file__).resolve()), "Install a wheel, not editable source."
    from mangroveai.models import UserMetrics as LegacyUserMetrics

    import mangroveai  # noqa: F401 - deliberately exercise the compatibility shim
    from mangrove_ai.models import UserMetrics

    assert LegacyUserMetrics is UserMetrics
    assert importlib.metadata.version("mangroveai") == mangrove_ai.__version__
    fixtures = Path(__file__).resolve().parents[1] / "contracts" / "mangroveai" / "fixtures"

    def fixture(name: str) -> dict:
        return json.loads((fixtures / f"{name}.json").read_text())

    calls = []
    fixture_key = "prod_distribution_fixture_not_a_real_key"

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.headers["Authorization"] == f"Bearer {fixture_key}"
        assert request.extensions["timeout"]["read"] == 2
        if request.url.path == "/api/v1/users/me/metrics":
            return httpx.Response(200, json=fixture("usage-success"))
        if request.url.path == "/api/v1/signals/":
            page = "one" if request.url.params["offset"] == "0" else "two"
            return httpx.Response(200, json=fixture(f"signals-page-{page}"))
        if request.url.path == "/api/v1/oracle/results":
            offset = int(request.url.params["offset"])
            return httpx.Response(200, json={
                "total": 2, "offset": offset, "limit": 1,
                "results": [{"result_id": f"row-{offset}", "max_drawdown": 0.1}],
            })
        if request.url.path == "/api/v1/fixture/payment":
            return httpx.Response(402, json={"error": "payment_required", "message": fixture_key})
        return httpx.Response(200, text="not JSON")

    with MangroveAI(
        api_key=fixture_key, load_dotenv=False, auto_retry=False, timeout=2,
        httpx_client=httpx.Client(transport=httpx.MockTransport(handler)),
    ) as client:
        assert client.users.get_my_metrics().messages_count == 7
        assert [row.name for row in client.signals.list_iter(limit_per_page=1)] == ["fixture_one", "fixture_two"]
        assert [row["result_id"] for row in client.oracle.list_results_iter(page_size=1)] == ["row-0", "row-1"]
        try:
            client._core_transport.request("GET", "/fixture/payment")
        except PaymentRequiredError as exc:
            assert fixture_key not in str(exc)
        else:
            raise AssertionError("402 was not preserved")
        try:
            client._core_transport.request("GET", "/fixture/malformed")
        except MalformedResponseError:
            pass
        else:
            raise AssertionError("Malformed success was accepted")
    assert len(calls) == 7
    print(json.dumps({
        "distribution": "mangroveai", "version": mangrove_ai.__version__,
        "requests_intercepted": len(calls),
    }))


if __name__ == "__main__":
    main()
