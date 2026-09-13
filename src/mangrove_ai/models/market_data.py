"""Models for the market-data regime readings (``client.market_data``).

Field names, units and null semantics match the MangroveAI copilot's
``get_market_regime`` and ``classify_market_segment`` tools, so code written against
either reads the same values. Percent-typed fields are on a 0-100 scale: ``12.5``
means 12.5%, not 1250%.
"""
from __future__ import annotations

from typing import Any

from ._base import MangroveModel


class DirectionReading(MangroveModel):
    """The direction band over one horizon.

    Either ``return_pct`` + ``band`` are set, or -- when the history is too short for
    that horizon -- ``error`` (e.g. ``"insufficient_history"``) and ``bars``.
    """

    return_pct: float | None = None
    """Return over the horizon, percent on a 0-100 scale."""
    band: str | None = None
    """Direction band, e.g. ``bull`` / ``neutral`` / ``bear``."""
    error: str | None = None
    bars: int | None = None


class VolatilityReading(MangroveModel):
    """One asset-relative volatility read, or ``error`` when the baseline is too short."""

    vol_ann_pct: float | None = None
    """Annualised volatility, percent on a 0-100 scale."""
    z_vs_baseline: float | None = None
    """Z-score of current volatility against the asset's own rolling baseline."""
    bucket: str | None = None
    """``low`` / ``medium`` / ``high``."""
    error: str | None = None


class RegimeReading(MangroveModel):
    """The regime service's classification, unchanged."""

    asof: str | None = None
    """The last date read."""
    direction: dict[str, DirectionReading] = {}
    """Keyed by horizon: ``"90d"``, ``"180d"``, ``"365d"``."""
    volatility: VolatilityReading | None = None
    asset: str | None = None


class MarketRegime(MangroveModel):
    """An asset's current market regime (``GET /market-data/regime/{asset}``)."""

    asset: str
    bars: int
    """How many daily closes the classification was made from."""
    regime: RegimeReading


class SegmentFeatures(MangroveModel):
    """The three features a segment's labels were read from."""

    total_return_pct: float | None = None
    """Percent, 0-100 scale."""
    realized_vol_ann_pct: float | None = None
    """Annualised realised volatility, percent, 0-100 scale."""
    r_squared: float | None = None
    """0 to 1 -- how closely the path tracked a straight line."""


class MarketSegment(MangroveModel):
    """What one named stretch of market was like (``GET /market-data/segment``).

    Every field is always present on the wire; one the regime service did not return
    is ``None``.
    """

    asset: str | None = None
    timeframe: str | None = None
    """The candle size the stretch was read at."""
    start_date: str | None = None
    end_date: str | None = None
    bars: int | None = None
    duration_days: int | None = None
    """Stretch length in days; selects the volatility band."""
    direction: str | None = None
    """``mega_bear`` through ``mega_bull``."""
    volatility: str | None = None
    """``low`` / ``medium`` / ``high``, or ``unscored`` when no fitted band covers the length."""
    trend: str | None = None
    """``clean`` / ``mixed`` / ``choppy``."""
    regime_composite: str | None = None
    """The three joined, e.g. ``bear_medium_mixed``."""
    scale: str | None = None
    """The fitted length band used, or ``None`` when none applied."""
    market_era: str | None = None
    scale_bands: list[dict[str, Any]] | None = None
    """Stretch lengths that have a fitted volatility band."""
    features: SegmentFeatures | None = None
