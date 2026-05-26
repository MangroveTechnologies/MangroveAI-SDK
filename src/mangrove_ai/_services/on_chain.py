from __future__ import annotations

from typing import Any

from ..models.on_chain import (
    ExchangeFlowsResponse,
    SmartMoneyScreenResponse,
    SmartMoneySentimentResponse,
    TokenHoldersResponse,
    WhaleActivityResponse,
    WhaleTransactionsResponse,
)
from ._base import BaseService


class OnChainService(BaseService):
    """On-chain analytics via Nansen and WhaleAlert."""

    def get_smart_money_sentiment(self, symbol: str, *, chain: str | None = None) -> SmartMoneySentimentResponse:
        """Get smart money sentiment for a token.

        Args:
            symbol: Token symbol (e.g. "ETH").
            chain: Optional chain filter (e.g. "ethereum").
        """
        params: dict[str, Any] = {"symbol": symbol}
        if chain is not None:
            params["chain"] = chain
        return self._request_model("GET", "/on-chain/smart-money/sentiment", SmartMoneySentimentResponse, params=params)

    def screen_smart_money(
        self, *, chains: list[str] | None = None, timeframe: str = "24h", limit: int = 20,
    ) -> SmartMoneyScreenResponse:
        """Screen tokens by smart money activity.

        Args:
            chains: Optional chain filter (comma-separated in request).
            timeframe: Lookback window (e.g. "1h", "24h", "7d").
            limit: Max tokens to return.
        """
        params: dict[str, Any] = {"timeframe": timeframe, "limit": limit}
        if chains is not None:
            params["chains"] = ",".join(chains)
        return self._request_model("GET", "/on-chain/smart-money/screen", SmartMoneyScreenResponse, params=params)

    def get_token_holders(self, symbol: str) -> TokenHoldersResponse:
        """Get token holder distribution and concentration.

        Args:
            symbol: Token symbol (e.g. "ETH").
        """
        return self._request_model("GET", f"/on-chain/token-holders/{symbol}", TokenHoldersResponse)

    def get_whale_transactions(
        self, *, symbol: str | None = None, min_value: float = 500_000, hours_back: int = 24,
    ) -> WhaleTransactionsResponse:
        """Get recent large-value on-chain transactions.

        Args:
            symbol: Optional token filter.
            min_value: Minimum USD value threshold.
            hours_back: Lookback window in hours.
        """
        params: dict[str, Any] = {"min_value": min_value, "hours_back": hours_back}
        if symbol is not None:
            params["symbol"] = symbol
        return self._request_model("GET", "/on-chain/whale-transactions", WhaleTransactionsResponse, params=params)

    def get_exchange_flows(self, *, symbol: str | None = None, hours_back: int = 24) -> ExchangeFlowsResponse:
        """Get aggregated exchange inflows/outflows.

        Args:
            symbol: Optional token filter (query param, not path).
            hours_back: Lookback window in hours.
        """
        params: dict[str, Any] = {"hours_back": hours_back}
        if symbol is not None:
            params["symbol"] = symbol
        return self._request_model("GET", "/on-chain/exchange-flows", ExchangeFlowsResponse, params=params)

    def get_whale_activity(self, symbol: str, *, hours_back: int = 24) -> WhaleActivityResponse:
        """Get high-level whale activity summary for a token.

        Args:
            symbol: Token symbol (e.g. "BTC").
            hours_back: Lookback window in hours.
        """
        params: dict[str, Any] = {"hours_back": hours_back}
        return self._request_model(
            "GET", f"/on-chain/whale-activity/{symbol}", WhaleActivityResponse, params=params,
        )
