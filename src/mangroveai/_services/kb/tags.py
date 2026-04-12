from __future__ import annotations

from ...models.kb import KBTag, KBTagDocuments
from .._base import BaseService


class KBTagsService(BaseService):
    """KB tag listing and filtering."""

    def list(self) -> list[KBTag]:
        """List all tags with document counts."""
        data = self._request("GET", "/tags")
        return [KBTag.model_validate(t) for t in data["tags"]]

    def get(self, tag: str) -> KBTagDocuments:
        """Get all documents with a specific tag."""
        return self._request_model("GET", f"/tags/{tag}", KBTagDocuments)
