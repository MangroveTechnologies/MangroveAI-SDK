from __future__ import annotations

from ...models.kb import KBDocument, KBDocumentSections, KBDocumentSummary
from .._base import BaseService


class KBDocumentsService(BaseService):
    """KB document listing and retrieval."""

    def list(self) -> list[KBDocumentSummary]:
        """List all documents in the knowledge base (summaries only)."""
        data = self._request("GET", "/documents")
        return [KBDocumentSummary.model_validate(d) for d in data["documents"]]

    def get(self, slug: str) -> KBDocument:
        """Get a full document by slug."""
        return self._request_model("GET", f"/documents/{slug}", KBDocument)

    def get_sections(self, slug: str) -> KBDocumentSections:
        """Get the section tree for a document."""
        return self._request_model("GET", f"/documents/{slug}/sections", KBDocumentSections)
