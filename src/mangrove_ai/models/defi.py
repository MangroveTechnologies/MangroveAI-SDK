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


# --- DeFi Pro (require a Pro / Startup / Enterprise plan) ---------------------
# These map to the tier-gated MangroveAI /defi/* Pro endpoints. Each returns a
# uniform {success, count, data} envelope where `data` is the raw DeFiLlama Pro
# payload (a list of records). The client raises on the 403
# (TIER_UPGRADE_REQUIRED) returned when the caller's plan is not entitled.


class TokenUnlocksResponse(MangroveModel):
    """Token unlock schedules + supply metrics (supply-shock signal). Pro."""

    success: bool
    count: int | None = None
    data: list[dict[str, Any]] | None = None


class PerpFundingResponse(MangroveModel):
    """Aggregated DeFi perpetual funding rates across venues. Pro."""

    success: bool
    count: int | None = None
    data: list[dict[str, Any]] | None = None


class TreasuriesResponse(MangroveModel):
    """Protocol treasury holdings (crowd-positioning signal). Pro."""

    success: bool
    count: int | None = None
    data: list[dict[str, Any]] | None = None


class EtfFlowsResponse(MangroveModel):
    """Crypto ETF net flows (institutional flow signal). Pro."""

    success: bool
    count: int | None = None
    data: list[dict[str, Any]] | None = None


class LendingRatesResponse(MangroveModel):
    """Lending-pool borrow rates (rate-spread features). Pro."""

    success: bool
    count: int | None = None
    data: list[dict[str, Any]] | None = None
