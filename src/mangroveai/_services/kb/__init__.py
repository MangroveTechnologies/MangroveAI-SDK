from __future__ import annotations

from functools import cached_property

from ..._transport._service import ServiceTransport
from .compute import KBComputeService
from .documents import KBDocumentsService
from .glossary import KBGlossaryService
from .indicators import KBIndicatorsService
from .search import KBSearchService
from .signals import KBSignalsService
from .tags import KBTagsService


class KBNamespace:
    """Knowledge Base API namespace.

    Groups all KB sub-services under client.kb:
        client.kb.documents.list()
        client.kb.search.query("RSI divergence")
        client.kb.signals.get("rsi_oversold")
    """

    def __init__(self, transport: ServiceTransport) -> None:
        self._transport = transport

    @cached_property
    def documents(self) -> KBDocumentsService:
        return KBDocumentsService(self._transport)

    @cached_property
    def search(self) -> KBSearchService:
        return KBSearchService(self._transport)

    @cached_property
    def tags(self) -> KBTagsService:
        return KBTagsService(self._transport)

    @cached_property
    def glossary(self) -> KBGlossaryService:
        return KBGlossaryService(self._transport)

    @cached_property
    def signals(self) -> KBSignalsService:
        return KBSignalsService(self._transport)

    @cached_property
    def indicators(self) -> KBIndicatorsService:
        return KBIndicatorsService(self._transport)

    @cached_property
    def compute(self) -> KBComputeService:
        return KBComputeService(self._transport)
