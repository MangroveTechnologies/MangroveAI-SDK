from __future__ import annotations

from ..._transport._service import ServiceTransport
from ...models.kb import KBBacklinksResponse, KBGlossaryEntry, KBGlossaryLookup, KBGlossaryResponse
from .._base import BaseService
from ..knowledge import KnowledgeService


class KBGlossaryService(BaseService):
    """KB glossary and cross-reference navigation."""

    def __init__(self, transport: ServiceTransport, knowledge: KnowledgeService) -> None:
        super().__init__(transport)
        self._knowledge = knowledge

    def lookup(self, term: str) -> KBGlossaryLookup:
        return self._knowledge.glossary(term)

    def list(self) -> KBGlossaryResponse:
        """Get the full glossary with all terms."""
        return self._request_model("GET", "/glossary", KBGlossaryResponse)

    def get(self, term: str) -> KBGlossaryEntry:
        """Get a specific glossary term with backlinks."""
        return self.lookup(term).entry

    def backlinks(self, anchor: str) -> KBBacklinksResponse:
        """Get all documents/sections that reference an anchor."""
        return self._request_model("GET", f"/backlinks/{anchor}", KBBacklinksResponse)
