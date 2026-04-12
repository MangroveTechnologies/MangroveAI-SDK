from __future__ import annotations

from typing import Any

from ._base import MangroveModel


class ProtocolTVLResponse(MangroveModel):
    """Total value locked for a DeFi protocol."""

    success: bool
    protocol: str
    tvl_usd: float | None = None
    chains: dict[str, float] | None = None
    data: dict[str, Any] | None = None


class ChainTVLResponse(MangroveModel):
    """Total value locked for a blockchain."""

    success: bool
    chain: str
    tvl_usd: float | None = None
    top_protocols: list[dict[str, Any]] | None = None
    data: dict[str, Any] | None = None


class StablecoinMetricsResponse(MangroveModel):
    """Global stablecoin supply and metrics."""

    success: bool
    total_supply_usd: float | None = None
    supply_by_chain: dict[str, float] | None = None
    data: dict[str, Any] | None = None
