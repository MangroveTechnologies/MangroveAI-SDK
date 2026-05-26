from __future__ import annotations

from typing import Any

from ._base import MangroveModel

# -- Documents --

class KBDocumentSummary(MangroveModel):
    """Document summary (no full content)."""

    slug: str
    title: str
    summary: str | None = None
    tags: list[str] | None = None
    section_count: int | None = None


class KBSection(MangroveModel):
    """A section within a document."""

    anchor: str | None = None
    title: str | None = None
    level: int | None = None
    content: str | None = None
    children: list[KBSection] | None = None


class KBDocument(MangroveModel):
    """Full document with content and sections."""

    slug: str
    title: str
    content: str | None = None
    summary: str | None = None
    tags: list[str] | None = None
    sections: list[KBSection] | None = None


class KBDocumentSections(MangroveModel):
    """Section tree for a document."""

    document_slug: str
    document_title: str
    sections: list[KBSection] | None = None


# -- Search --

class KBSearchResult(MangroveModel):
    """A single search result."""

    title: str | None = None
    content: str | None = None
    snippet: str | None = None
    document_slug: str | None = None
    document_title: str | None = None
    section_anchor: str | None = None
    relevance_score: float | None = None
    tags: list[str] | None = None


class KBSearchResponse(MangroveModel):
    """Response from GET /search."""

    query: str | None = None
    total: int | None = None
    results: list[KBSearchResult]


# -- Tags --

class KBTag(MangroveModel):
    """A tag with document count."""

    name: str
    count: int


class KBTagDocuments(MangroveModel):
    """Documents associated with a tag."""

    tag: str
    total: int
    documents: list[dict[str, Any]]


# -- Glossary --

class KBGlossaryEntry(MangroveModel):
    """A glossary term definition."""

    term: str
    abbreviation: str | None = None
    definition: str | None = None
    anchor: str | None = None
    document_slug: str | None = None
    backlinks: list[dict[str, Any]] | None = None


class KBGlossaryResponse(MangroveModel):
    """Full glossary listing."""

    total: int
    entries: list[KBGlossaryEntry]


class KBBacklinksResponse(MangroveModel):
    """Backlinks for an anchor."""

    target_anchor: str
    total: int
    backlinks: list[dict[str, Any]]


# -- Signals & Indicators --

class KBSignal(MangroveModel):
    """A signal from the KB (metadata perspective)."""

    name: str
    category: str | None = None
    signal_type: str | None = None
    description: str | None = None
    params: dict[str, Any] | None = None
    requires: list[str] | None = None


class KBIndicator(MangroveModel):
    """An indicator from the KB."""

    name: str
    category: str | None = None
    description: str | None = None
    params: Any | None = None
    outputs: Any | None = None


# -- Compute (x402) --

class KBComputeResult(MangroveModel):
    """Result from x402 compute endpoints."""

    signal: str | None = None
    indicator: str | None = None
    result: Any = None
