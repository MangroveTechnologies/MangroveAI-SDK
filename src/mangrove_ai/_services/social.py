from __future__ import annotations

from typing import Any
from urllib.parse import quote

from ..models.social import InfluenceScoreResponse, MentionsResponse, SentimentResponse
from ._base import BaseService


class SocialService(BaseService):
    """Social signal analytics via X/Twitter."""

    def get_sentiment(self, topic: str, *, hours_back: int = 24) -> SentimentResponse:
        """Get social sentiment for a topic.

        Args:
            topic: Topic or asset symbol to analyze.
            hours_back: Lookback window in hours.
        """
        params: dict[str, Any] = {"hours_back": hours_back}
        return self._request_model("GET", f"/social/sentiment/{quote(topic, safe='')}", SentimentResponse, params=params)

    def get_mentions(self, topic: str, *, hours_back: int = 24, limit: int = 20) -> MentionsResponse:
        """Get recent social mentions for a topic.

        Args:
            topic: Topic or asset symbol.
            hours_back: Lookback window in hours.
            limit: Max posts to return.
        """
        params: dict[str, Any] = {"hours_back": hours_back, "limit": limit}
        return self._request_model("GET", f"/social/mentions/{quote(topic, safe='')}", MentionsResponse, params=params)

    def get_influence_score(self, username: str) -> InfluenceScoreResponse:
        """Get influence score for a social account.

        Args:
            username: X/Twitter username.
        """
        return self._request_model("GET", f"/social/influence/{quote(username, safe='')}", InfluenceScoreResponse)

    def get_social_sentiment(self, topic: str, *, hours_back: int = 24) -> SentimentResponse:
        """Canonical-name alias for social sentiment."""
        return self.get_sentiment(topic, hours_back=hours_back)

    def get_social_mentions(self, topic: str, *, hours_back: int = 24, limit: int = 20) -> MentionsResponse:
        """Canonical-name alias for social mentions."""
        return self.get_mentions(topic, hours_back=hours_back, limit=limit)
