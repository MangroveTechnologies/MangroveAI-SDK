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


class SignalBehaviorResult(MangroveModel):
    """Response from POST /signals/behavior (``client.signals.query_signal_behavior``).

    ``result`` is the lookup's answer, shaped per lookup exactly as the copilot's
    ``query_signal_behavior`` tool returns it:

    - ``describe``: ``signal``, ``signal_type``, ``category``, ``description``,
      ``parameters`` (each ``type``/``min``/``max``/``default``/``means``), ``measured``,
      and when measured the span -- FILTER ``selectivity_min``/``_median``/``_max``
      (fractions 0-1), ``typical_run_bars``, ``longest_run_bars``; TRIGGER
      ``per_1000_bars_min``/``_median``/``_max``, ``typical_gap_bars``,
      ``shortest_gap_bars``, ``stays_true_over_one_bar`` -- plus ``default``.
    - ``pick``: ``measured``, ``measured_in``, ``span``, ``matches``, ``unreachable``
      (``None`` when the target was met) and ``configurations``.
    - ``find``: ``measured_in``, ``band`` and ``signals`` (each with one ``example``).
    - ``gap_probability``: ``range_bars``, ``matches`` and ``configurations`` (each with
      ``probability``, ``gaps_in_range``, ``gaps_total``).

    Configuration rows always carry ``params``, ``fired_bars`` and ``is_default``; FILTER
    rows add ``selectivity`` (0-1), ``runs``, ``mean_run_bars``, ``longest_run_bars``;
    TRIGGER rows add ``per_1000_bars``, ``median_gap_bars``, ``shortest_gap_bars``,
    ``longest_gap_bars``, ``stays_true_bars``. ``measured: False`` means the signal has
    no measurements yet -- an answer, not an error.
    """

    lookup: str
    result: dict[str, Any]
