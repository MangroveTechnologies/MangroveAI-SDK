from __future__ import annotations

from ._base import MangroveModel


class DocItem(MangroveModel):
    """A documentation file entry."""

    path: str
    name: str
    title: str | None = None


class DocContentResponse(MangroveModel):
    """Response from GET /docs/content."""

    success: bool
    content: str
    path: str
    error: str | None = None
