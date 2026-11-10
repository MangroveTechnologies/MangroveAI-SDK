from __future__ import annotations

from typing import Any

from ._base import MangroveModel


class ProtocolTVLResponse(MangroveModel):
    """Total value locked for a DeFi protocol."""

    success: bool
    provider: str | None = None
    protocol: str
    tvl_usd: float | None = None
    chains: dict[str, float] | None = None
    data: dict[str, Any] | None = None


class ChainTVLResponse(MangroveModel):
    """Total value locked for a blockchain."""

    success: bool
    provider: str | None = None
    chain: str
    tvl_usd: float | None = None
    top_protocols: list[dict[str, Any]] | None = None
    data: dict[str, Any] | None = None


class StablecoinMetricsResponse(MangroveModel):
    """Global stablecoin supply and metrics."""

    success: bool
    provider: str | None = None
    total_supply_usd: float | None = None
    supply_by_chain: dict[str, float] | None = None
    data: dict[str, Any] | None = None


# --- DeFi Pro (require a Pro / Startup / Enterprise plan) ---------------------


class DeFiPageResponse(MangroveModel):
    """One page of projected provider records, preserving the existing data envelope.

    Pagination fields are optional for compatibility with older servers. Missing
    metadata is unknown, not a claim that this page covers the complete dataset.
    ``count`` counts this page; ``total`` counts all matching readable records.
    """

    success: bool
    provider: str | None = None
    count: int | None = None
    data: list[dict[str, Any]] | dict[str, Any] | None = None
    total: int | None = None
    offset: int | None = None
    limit: int | None = None
    has_more: bool | None = None
    next_offset: int | None = None
    skipped: int | None = None


class TokenUnlocksResponse(DeFiPageResponse):
    """Token unlock schedules and supply metrics. Pro."""

    window: dict[str, Any] | None = None


class PerpFundingResponse(DeFiPageResponse):
    """DeFi perpetual funding rates across venues. Pro."""


class TreasuriesResponse(DeFiPageResponse):
    """Protocol treasury holdings. Pro."""


class EtfFlowsResponse(DeFiPageResponse):
    """Daily ETF flows and totals across the entire requested window. Pro."""

    window: dict[str, Any] | None = None
    totals: list[dict[str, Any]] | None = None


class LendingRatesResponse(DeFiPageResponse):
    """Lending-pool borrow rates. Pro."""
