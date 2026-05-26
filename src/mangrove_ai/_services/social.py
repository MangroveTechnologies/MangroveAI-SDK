from __future__ import annotations

from typing import Any

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
        return self._request_model("GET", f"/social/sentiment/{topic}", SentimentResponse, params=params)

    def get_mentions(self, topic: str, *, hours_back: int = 24, limit: int = 20) -> MentionsResponse:
        """Get recent social mentions for a topic.

        Args:
            topic: Topic or asset symbol.
            hours_back: Lookback window in hours.
            limit: Max posts to return.
        """
        params: dict[str, Any] = {"hours_back": hours_back, "limit": limit}
        return self._request_model("GET", f"/social/mentions/{topic}", MentionsResponse, params=params)

    def get_influence_score(self, username: str) -> InfluenceScoreResponse:
        """Get influence score for a social account.

        Args:
            username: X/Twitter username.
        """
        return self._request_model("GET", f"/social/influence/{username}", InfluenceScoreResponse)
