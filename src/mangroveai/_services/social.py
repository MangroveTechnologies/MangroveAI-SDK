from __future__ import annotations

from ..exceptions import NotImplementedLayerError
from ._base import BaseService

_MSG = "Social analytics endpoints are not yet available. Expected in a future SDK release."


class SocialService(BaseService):
    """Social signal analytics (Layer 3 -- not yet implemented)."""

    def get_sentiment(self, topic: str, *, hours_back: int = 24) -> None:
        raise NotImplementedLayerError(_MSG)

    def get_mentions(self, topic: str, *, hours_back: int = 24, limit: int = 20) -> None:
        raise NotImplementedLayerError(_MSG)

    def get_influence_score(self, username: str) -> None:
        raise NotImplementedLayerError(_MSG)
