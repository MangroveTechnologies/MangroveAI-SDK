from __future__ import annotations

from ..._transport._service import ServiceTransport
from ...models.kb import KBDocument, KBDocumentList, KBDocumentSections, KBDocumentSummary
from .._base import BaseService
from ..knowledge import KnowledgeService


class KBDocumentsService(BaseService):
    """Compatibility namespace for the canonical document operations."""

    def __init__(self, transport: ServiceTransport, knowledge: KnowledgeService) -> None:
        super().__init__(transport)
        self._knowledge = knowledge

    def list(self) -> list[KBDocumentSummary]:
        return self.list_result().documents

    def list_result(self) -> KBDocumentList:
        """Return the complete listing, including artifact provenance."""
        return self._knowledge.list_documents()

    def get(
        self,
        slug: str,
        *,
        max_chars: int | None = None,
        offset: int = 0,
        full: bool = False,
        view: str = "content",
        section_anchor: str | None = None,
    ) -> KBDocument:
        return self._knowledge.get_document(
            slug, max_chars=max_chars, offset=offset, full=full, view=view, section_anchor=section_anchor
        )

    def get_sections(self, slug: str) -> KBDocumentSections:
        doc = self.get(slug, full=True)
        return KBDocumentSections(
            document_slug=doc.slug,
            document_title=doc.title,
            sections=doc.sections,
            source=doc.source,
        )
