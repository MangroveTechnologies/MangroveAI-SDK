from __future__ import annotations

from typing import Any

from ._base import MangroveModel


class SmartMoneySentimentResponse(MangroveModel):
    """Smart money sentiment for a token."""

    success: bool
    symbol: str
    chain: str | None = None
    sentiment: str | None = None
    smart_money_inflow_usd: float | None = None
    smart_money_outflow_usd: float | None = None
    net_flow_usd: float | None = None
    trend_7d: str | None = None
    data: dict[str, Any] | None = None


class SmartMoneyScreenResponse(MangroveModel):
    """Screened tokens by smart money activity."""

    success: bool
    count: int | None = None
    chains: list[str] | None = None
    timeframe: str | None = None
    tokens: list[dict[str, Any]] | None = None


class TokenHoldersResponse(MangroveModel):
    """Token holder distribution."""

    success: bool
    symbol: str
    holder_count: int | None = None
    top_10_holders_pct: float | None = None
    concentration_score: float | None = None
    data: dict[str, Any] | None = None


class WhaleTransactionsResponse(MangroveModel):
    """Recent large-value on-chain transactions."""

    success: bool
    count: int | None = None
    min_value_usd: float | None = None
    transactions: list[dict[str, Any]] | None = None


class ExchangeFlowsResponse(MangroveModel):
    """Aggregated exchange inflows/outflows."""

    success: bool
    symbol: str | None = None
    timeframe: str | None = None
    net_flow_usd: float | None = None
    flows: list[dict[str, Any]] | None = None


class WhaleActivityResponse(MangroveModel):
    """High-level whale activity summary."""

    success: bool
    symbol: str
    hours_back: int | None = None
    summary: dict[str, Any] | None = None


class SmartMoneyHistoricalHoldingsResponse(MangroveModel):
    """Date-stamped snapshots of Smart Money token holdings."""

    success: bool
    chains: list[str] | None = None
    date_range: dict[str, str] | None = None
    count: int | None = None
    holdings: list[dict[str, Any]] | None = None


class SmartMoneyDexTradesResponse(MangroveModel):
    """Recent DEX trades from Smart Money wallets."""

    success: bool
    chains: list[str] | None = None
    count: int | None = None
    trades: list[dict[str, Any]] | None = None


class SmartMoneyPerpTradesResponse(MangroveModel):
    """Perpetual-futures trades from Smart Money wallets (Hyperliquid)."""

    success: bool
    venue: str | None = None
    count: int | None = None
    trades: list[dict[str, Any]] | None = None


class TokenDexTradesResponse(MangroveModel):
    """DEX trades for a single token across all participants in a date window."""

    success: bool
    symbol: str
    chain: str | None = None
    contract_address: str | None = None
    date_range: dict[str, str] | None = None
    count: int | None = None
    trades: list[dict[str, Any]] | None = None


class TokenFlowsResponse(MangroveModel):
    """Aggregated per-wallet-category flow data for a single token in a date window."""

    success: bool
    symbol: str
    chain: str | None = None
    contract_address: str | None = None
    label: str | None = None
    date_range: dict[str, str] | None = None
    count: int | None = None
    flows: list[dict[str, Any]] | None = None


class OnChainSeriesResponse(MangroveModel):
    """Per-bar on-chain metric series (one key per metric), indexed by timestamp.

    Each item in ``series`` is a row with a ``timestamp`` plus one key per requested
    metric (SmartMoneyNetflow, SmartMoneyHoldings, ExchangeNetflow, WhaleNetInflow,
    HolderConcentration). Build a pandas DataFrame with
    ``pd.DataFrame(resp.series).set_index("timestamp")``.
    """

    success: bool
    symbol: str
    chain: str | None = None
    interval: str | None = None
    date_range: dict[str, str] | None = None
    metrics: list[str] | None = None
    count: int | None = None
    series: list[dict[str, Any]] | None = None
