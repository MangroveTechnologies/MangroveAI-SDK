from __future__ import annotations

from typing import Any

from ._base import MangroveModel


class RiskScores(MangroveModel):
    """Multi-factor risk scoring for an asset."""

    market_cap: int | float | None = None
    liquidity: int | float | None = None
    exchange: int | float | None = None
    age: int | float | None = None
    volatility: int | float | None = None
    supply_distribution: int | float | None = None
    price_stability: int | float | None = None
    overall: float | None = None


class AssetMetadata(MangroveModel):
    """Supplementary asset metadata."""

    market_cap: float | None = None
    volume_24h: float | None = None
    age_days: int | None = None
    exchanges: list[str] | None = None


class AssetTimestamps(MangroveModel):
    """Lifecycle timestamps for an asset record."""

    created_at: str | None = None
    updated_at: str | None = None
    last_evaluated_at: str | None = None


class CryptoAsset(MangroveModel):
    """A cryptocurrency asset with risk scoring."""

    id: str | None = None
    symbol: str
    name: str
    risk_scores: RiskScores | None = None
    is_approved: bool | None = None
    regulatory_status: str | None = None
    security_status: str | None = None
    metadata: AssetMetadata | None = None
    timestamps: AssetTimestamps | None = None


class Exchange(MangroveModel):
    """A cryptocurrency exchange."""

    id: str | None = None
    name: str
    display_name: str | None = None
    tier: int | None = None
    exchange_type: str | None = None
    country: str | None = None
    region: str | None = None
    is_active: bool | None = None


class MarketDataResponse(MangroveModel):
    """Response from GET /crypto-assets/market-data/{symbol}."""

    success: bool
    symbol: str
    data: dict[str, Any]


class OHLCVResponse(MangroveModel):
    """Response from GET /crypto-assets/ohlcv/{symbol}."""

    success: bool
    symbol: str
    data_points: int | None = None
    data: Any = None


class TrendingResponse(MangroveModel):
    """Response from GET /crypto-assets/trending."""

    success: bool
    count: int | None = None
    trending: list[Any]


class GlobalMarketResponse(MangroveModel):
    """Response from GET /crypto-assets/global-market."""

    success: bool
    data: dict[str, Any]
