from __future__ import annotations

from typing import Any

from ..models.on_chain import (
    ExchangeFlowsResponse,
    SmartMoneyDexTradesResponse,
    SmartMoneyHistoricalHoldingsResponse,
    SmartMoneyPerpTradesResponse,
    SmartMoneyScreenResponse,
    SmartMoneySentimentResponse,
    TokenDexTradesResponse,
    TokenFlowsResponse,
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

    # ----- Tier-1 smart-money expansion (Nansen Pro plan) ---------------------

    def get_smart_money_historical_holdings(
        self,
        *,
        chains: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> SmartMoneyHistoricalHoldingsResponse:
        """Get date-stamped Smart Money holdings snapshots across chains.

        Args:
            chains: Chain filter (e.g. ["ethereum", "solana"]). Default: ["ethereum"].
            date_from: Start date in YYYY-MM-DD. Default: 7 days ago.
            date_to: End date in YYYY-MM-DD. Default: today.
            page: Page number.
            per_page: Page size.
        """
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if chains is not None:
            params["chains"] = ",".join(chains)
        if date_from is not None:
            params["from"] = date_from
        if date_to is not None:
            params["to"] = date_to
        return self._request_model(
            "GET",
            "/on-chain/smart-money/historical-holdings",
            SmartMoneyHistoricalHoldingsResponse,
            params=params,
        )

    def get_smart_money_dex_trades(
        self,
        *,
        chains: list[str] | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> SmartMoneyDexTradesResponse:
        """Get recent DEX trades from Smart Money wallets.

        Args:
            chains: Chain filter (e.g. ["ethereum"]).
            page: Page number.
            per_page: Page size.
        """
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if chains is not None:
            params["chains"] = ",".join(chains)
        return self._request_model(
            "GET",
            "/on-chain/smart-money/dex-trades",
            SmartMoneyDexTradesResponse,
            params=params,
        )

    def get_smart_money_perp_trades(
        self,
        *,
        page: int = 1,
        per_page: int = 100,
    ) -> SmartMoneyPerpTradesResponse:
        """Get perpetual-futures trades from Smart Money wallets on Hyperliquid.

        Hyperliquid-only -- no chain filter accepted.

        Args:
            page: Page number.
            per_page: Page size.
        """
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        return self._request_model(
            "GET",
            "/on-chain/smart-money/perp-trades",
            SmartMoneyPerpTradesResponse,
            params=params,
        )

    # ----- Tier-2 token-scoped expansion --------------------------------------

    def get_token_dex_trades(
        self,
        symbol: str,
        *,
        chain: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> TokenDexTradesResponse:
        """Get DEX trades for a single token across all participants in a date window.

        Args:
            symbol: Token symbol (e.g. "UNI").
            chain: Blockchain (default: "ethereum").
            date_from: Start date YYYY-MM-DD. Default: 7 days ago.
            date_to: End date YYYY-MM-DD. Default: today.
            page: Page number.
            per_page: Page size.
        """
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if chain is not None:
            params["chain"] = chain
        if date_from is not None:
            params["from"] = date_from
        if date_to is not None:
            params["to"] = date_to
        return self._request_model(
            "GET",
            f"/on-chain/token/{symbol}/dex-trades",
            TokenDexTradesResponse,
            params=params,
        )

    def get_token_flows(
        self,
        symbol: str,
        *,
        chain: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> TokenFlowsResponse:
        """Get aggregated per-wallet-category flow data for a single token in a date window.

        Stablecoins are not supported on this endpoint -- returns 404.

        Args:
            symbol: Token symbol (e.g. "UNI"). Stablecoins are rejected.
            chain: Blockchain (default: "ethereum").
            date_from: Start date YYYY-MM-DD. Default: 7 days ago.
            date_to: End date YYYY-MM-DD. Default: today.
            page: Page number.
            per_page: Page size.
        """
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if chain is not None:
            params["chain"] = chain
        if date_from is not None:
            params["from"] = date_from
        if date_to is not None:
            params["to"] = date_to
        return self._request_model(
            "GET",
            f"/on-chain/token/{symbol}/flows",
            TokenFlowsResponse,
            params=params,
        )
