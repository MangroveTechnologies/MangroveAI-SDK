from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

from ..models.kb import KBDocument, KBDocumentList, KBGlossaryLookup, KBSearchResponse, KnowledgeAnswer
from ._base import BaseService


class KnowledgeService(BaseService):
    """Canonical knowledge operations served by MangroveAI."""

    def list_documents(self) -> KBDocumentList:
        return self._request_model("GET", "/knowledge/documents", KBDocumentList)

    def get_document(
        self,
        slug: str,
        *,
        max_chars: int | None = None,
        offset: int = 0,
        full: bool = False,
        view: str = "content",
        section_anchor: str | None = None,
    ) -> KBDocument:
        params = {"offset": offset, "full": str(full).lower(), "view": view}
        if section_anchor is not None:
            params["section_anchor"] = section_anchor
        if max_chars is not None:
            params["max_chars"] = max_chars
        return self._request_model(
            "GET",
            f"/knowledge/documents/{quote(slug, safe='')}",
            KBDocument,
            params=params,
        )

    def quick_reference(
        self,
        *,
        max_chars: int | None = None,
        offset: int = 0,
        full: bool = False,
        view: str = "content",
        section_anchor: str | None = None,
    ) -> KBDocument:
        params = {"offset": offset, "full": str(full).lower(), "view": view}
        if section_anchor is not None:
            params["section_anchor"] = section_anchor
        if max_chars is not None:
            params["max_chars"] = max_chars
        return self._request_model("GET", "/knowledge/quick-reference", KBDocument, params=params)

    def search(
        self,
        q: str,
        *,
        tag: str | None = None,
        tags: list[str] | None = None,
        expand: bool = True,
        limit: int | None = None,
    ) -> KBSearchResponse:
        params: dict[str, Any] = {"q": q, "expand": str(expand).lower()}
        if tag is not None:
            params["tag"] = tag
        if tags is not None:
            params["tags"] = json.dumps(tags)
        if limit is not None:
            params["limit"] = limit
        return self._request_model("GET", "/knowledge/search", KBSearchResponse, params=params)

    def glossary(self, term: str) -> KBGlossaryLookup:
        return self._request_model("GET", "/knowledge/glossary", KBGlossaryLookup, params={"term": term})

    def query(self, op: str, **arguments: Any) -> KnowledgeAnswer:
        return self._request_model("POST", "/knowledge/query", KnowledgeAnswer, json={"op": op, **arguments})
