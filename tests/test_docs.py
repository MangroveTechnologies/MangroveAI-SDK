from __future__ import annotations

from mangroveai import MangroveAI
from mangroveai._transport._mock import MockTransport
from mangroveai.models.docs import DocContentResponse, DocItem


def _make_client(mock: MockTransport) -> MangroveAI:
    return MangroveAI(api_key="test_abc123", environment="local", httpx_client=mock)


class TestDocsList:
    def test_list_returns_doc_items(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/docs/list", json={
            "success": True,
            "docs": [
                {"path": "api/authentication.md", "name": "authentication.md", "title": "Authentication"},
                {"path": "api/backtesting.md", "name": "backtesting.md", "title": "Backtesting"},
            ],
        })
        client = _make_client(mock)

        result = client.docs.list()

        assert len(result) == 2
        assert isinstance(result[0], DocItem)
        assert result[0].path == "api/authentication.md"
        assert result[1].title == "Backtesting"

    def test_list_empty(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/docs/list", json={
            "success": True,
            "docs": [],
        })
        client = _make_client(mock)

        result = client.docs.list()

        assert result == []


class TestDocsGetContent:
    def test_get_content_returns_markdown(self) -> None:
        mock = MockTransport()
        mock.add_response("GET", "/docs/content", json={
            "success": True,
            "content": "# Authentication\n\nUse Bearer tokens...",
            "path": "api/authentication.md",
        })
        client = _make_client(mock)

        result = client.docs.get_content("api/authentication.md")

        assert isinstance(result, DocContentResponse)
        assert result.success is True
        assert result.content.startswith("# Authentication")
        assert result.path == "api/authentication.md"
        assert mock.requests[0].params == {"path": "api/authentication.md"}
