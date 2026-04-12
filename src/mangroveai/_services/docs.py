from __future__ import annotations

from ..models.docs import DocContentResponse, DocItem
from ._base import BaseService


class DocsService(BaseService):
    """Documentation listing and content retrieval."""

    def list(self) -> list[DocItem]:
        """List all available documentation files."""
        return self._request_list("GET", "/docs/list", DocItem, key="docs")

    def get_content(self, path: str) -> DocContentResponse:
        """Get raw markdown content for a documentation file.

        Args:
            path: Document path (e.g. "api/authentication.md").
        """
        return self._request_model("GET", "/docs/content", DocContentResponse, params={"path": path})
