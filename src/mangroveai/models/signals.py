from __future__ import annotations

from typing import Any

from ._base import MangroveModel


class SignalMetadata(MangroveModel):
    """Signal function metadata."""

    rule_name: str | None = None
    description: str | None = None
    requires: list[str] | None = None
    params: dict[str, Any] | None = None


class Signal(MangroveModel):
    """A trading signal with its metadata."""

    name: str
    category: str
    signal_type: str | None = None
    metadata: SignalMetadata | None = None
    code: str | None = None
    usage_count: int | None = None


class SearchSignalsRequest(MangroveModel):
    """Request body for POST /signals/search."""

    query: str
    search_type: str = "name"
    limit: int = 50
    offset: int = 0


class MatchResult(MangroveModel):
    """A single signal match from semantic matching."""

    signal_name: str
    description: str | None = None
    similarity_score: float | None = None
    semantic_score: float | None = None
    intent_score: float | None = None
    usecase_score: float | None = None
    params: dict[str, Any] | None = None
    match_reasoning: str | None = None


class MatchResponse(MangroveModel):
    """Response from POST /signals/match."""

    query: str
    top_k: int
    similarity_threshold: float
    matches: list[MatchResult]


class EvaluateResponse(MangroveModel):
    """Response from signal evaluation."""

    success: bool
    result: bool | None = None
    error: str | None = None


class ValidationResponse(MangroveModel):
    """Response from signal validation."""

    valid: bool
    errors: list[str] | None = None
