from __future__ import annotations

from ...models.kb import KBBacklinksResponse, KBGlossaryEntry, KBGlossaryResponse
from .._base import BaseService


class KBGlossaryService(BaseService):
    """KB glossary and cross-reference navigation."""

    def list(self) -> KBGlossaryResponse:
        """Get the full glossary with all terms."""
        return self._request_model("GET", "/glossary", KBGlossaryResponse)

    def get(self, term: str) -> KBGlossaryEntry:
        """Get a specific glossary term with backlinks."""
        return self._request_model("GET", f"/glossary/{term}", KBGlossaryEntry)

    def backlinks(self, anchor: str) -> KBBacklinksResponse:
        """Get all documents/sections that reference an anchor."""
        return self._request_model("GET", f"/backlinks/{anchor}", KBBacklinksResponse)
