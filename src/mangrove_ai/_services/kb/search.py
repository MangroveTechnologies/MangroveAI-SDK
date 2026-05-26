from __future__ import annotations

from typing import Any

from ...models.kb import KBSearchResponse
from .._base import BaseService


class KBSearchService(BaseService):
    """KB full-text search."""

    def query(
        self,
        q: str,
        *,
        tags: list[str] | None = None,
        expand: bool = True,
        limit: int = 20,
    ) -> KBSearchResponse:
        """Search the knowledge base.

        Args:
            q: Search query text.
            tags: Optional tag filter (comma-joined in request).
            expand: Enable synonym/stem expansion.
            limit: Max results (1-100).
        """
        params: dict[str, Any] = {"q": q, "limit": limit, "expand": expand}
        if tags:
            params["tags"] = ",".join(tags)
        return self._request_model("GET", "/search", KBSearchResponse, params=params)
