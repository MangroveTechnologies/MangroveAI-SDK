from __future__ import annotations

from typing import Any

from ._base import MangroveModel


class SentimentResponse(MangroveModel):
    """Social sentiment for a topic."""

    success: bool
    topic: str
    sentiment: str | None = None
    score: float | None = None
    mentions: int | None = None
    data: dict[str, Any] | None = None


class MentionsResponse(MangroveModel):
    """Social mentions for a topic."""

    success: bool
    topic: str
    count: int | None = None
    posts: list[dict[str, Any]] | None = None


class InfluenceScoreResponse(MangroveModel):
    """Influence score for a social account."""

    success: bool
    username: str
    score: float | None = None
    followers: int | None = None
    data: dict[str, Any] | None = None
