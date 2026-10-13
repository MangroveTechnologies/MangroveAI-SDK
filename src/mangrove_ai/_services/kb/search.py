from __future__ import annotations

from ..._transport._service import ServiceTransport
from ...models.kb import KBSearchResponse
from .._base import BaseService
from ..knowledge import KnowledgeService


class KBSearchService(BaseService):
    """Compatibility namespace for canonical document search."""

    def __init__(self, transport: ServiceTransport, knowledge: KnowledgeService) -> None:
        super().__init__(transport)
        self._knowledge = knowledge

    def query(
        self,
        q: str,
        *,
        tags: list[str] | None = None,
        expand: bool = True,
        limit: int | None = 20,
    ) -> KBSearchResponse:
        result = self._knowledge.search(q, tags=tags, expand=expand, limit=limit)
        if result.total_results is not None:
            result.total = result.total_results
        return result
