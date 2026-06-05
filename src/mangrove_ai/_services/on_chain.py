from __future__ import annotations

from typing import Any

from ..models.on_chain import (
    ExchangeFlowsResponse,
    OnChainSeriesResponse,
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
    #
    # All five new methods POST a JSON body that mirrors the upstream Nansen
    # API shape, so customers get full filter + order_by passthrough -- they
    # can sort by ``value_usd DESC``, restrict to ``Fund``-labelled wallets,
    # bound ``value_usd`` between a min/max, etc.

    def get_smart_money_historical_holdings(
        self,
        *,
        chains: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        filters: dict[str, Any] | None = None,
        order_by: list[dict[str, str]] | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> SmartMoneyHistoricalHoldingsResponse:
        """Get date-stamped Smart Money holdings snapshots across chains.

        Args:
            chains: Chain filter (e.g. ["ethereum", "solana"]). Default: ["ethereum"].
            date_from: Start date YYYY-MM-DD. Default: 7 days ago.
            date_to: End date YYYY-MM-DD. Default: today.
            filters: Nansen-shape filter dict (include_smart_money_labels,
                value_usd: {min, max}, balance_24h_percent_change, token_age_days, ...).
            order_by: Nansen-shape order_by list, e.g.
                ``[{"field": "value_usd", "direction": "DESC"}]``.
            page: Page number.
            per_page: Page size.
        """
        body: dict[str, Any] = {"page": page, "per_page": per_page}
        if chains is not None:
            body["chains"] = chains
        if date_from is not None or date_to is not None:
            body["date_range"] = {
                k: v for k, v in {"from": date_from, "to": date_to}.items() if v is not None
            }
        if filters is not None:
            body["filters"] = filters
        if order_by is not None:
            body["order_by"] = order_by
        return self._request_model(
            "POST",
            "/on-chain/smart-money/historical-holdings",
            SmartMoneyHistoricalHoldingsResponse,
            json=body,
        )

    def get_smart_money_dex_trades(
        self,
        *,
        chains: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        order_by: list[dict[str, str]] | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> SmartMoneyDexTradesResponse:
        """Get recent DEX trades from Smart Money wallets.

        Args:
            chains: Chain filter (e.g. ["ethereum"]).
            filters: Nansen filter dict (include_smart_money_labels, token_address,
                side ['buy'|'sell'], min_amount_usd).
            order_by: Sort order, e.g. ``[{"field": "block_timestamp", "direction": "DESC"}]``.
            page: Page number.
            per_page: Page size.
        """
        body: dict[str, Any] = {"page": page, "per_page": per_page}
        if chains is not None:
            body["chains"] = chains
        if filters is not None:
            body["filters"] = filters
        if order_by is not None:
            body["order_by"] = order_by
        return self._request_model(
            "POST",
            "/on-chain/smart-money/dex-trades",
            SmartMoneyDexTradesResponse,
            json=body,
        )

    def get_smart_money_perp_trades(
        self,
        *,
        filters: dict[str, Any] | None = None,
        order_by: list[dict[str, str]] | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> SmartMoneyPerpTradesResponse:
        """Get perpetual-futures trades from Smart Money wallets on Hyperliquid.

        Hyperliquid-only; no chain filter accepted by upstream.

        Args:
            filters: Nansen filter dict (action, side ['Long'|'Short'], token_symbol,
                type ['Market'|'Limit'], value_usd: {min, max}, only_new_positions).
            order_by: Sort order (valid fields: block_timestamp, token_amount,
                price_usd, value_usd).
            page: Page number.
            per_page: Page size.
        """
        body: dict[str, Any] = {"page": page, "per_page": per_page}
        if filters is not None:
            body["filters"] = filters
        if order_by is not None:
            body["order_by"] = order_by
        return self._request_model(
            "POST",
            "/on-chain/smart-money/perp-trades",
            SmartMoneyPerpTradesResponse,
            json=body,
        )

    # ----- Tier-2 token-scoped expansion --------------------------------------

    def get_token_dex_trades(
        self,
        symbol: str,
        *,
        chain: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        filters: dict[str, Any] | None = None,
        order_by: list[dict[str, str]] | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> TokenDexTradesResponse:
        """Get DEX trades for a single token across all participants in a date window.

        Args:
            symbol: Token identifier (CoinGecko ID preferred, e.g. ``"uniswap"``).
            chain: Blockchain (default: "ethereum").
            date_from: Start date YYYY-MM-DD. Default: 7 days ago.
            date_to: End date YYYY-MM-DD. Default: today.
            filters: Nansen filter dict.
            order_by: Sort order.
            page: Page number.
            per_page: Page size.
        """
        body: dict[str, Any] = {"page": page, "per_page": per_page}
        if chain is not None:
            body["chain"] = chain
        if date_from is not None or date_to is not None:
            body["date_range"] = {
                k: v for k, v in {"from": date_from, "to": date_to}.items() if v is not None
            }
        if filters is not None:
            body["filters"] = filters
        if order_by is not None:
            body["order_by"] = order_by
        return self._request_model(
            "POST",
            f"/on-chain/token/{symbol}/dex-trades",
            TokenDexTradesResponse,
            json=body,
        )

    def get_token_flows(
        self,
        symbol: str,
        *,
        chain: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        label: str | None = None,
        filters: dict[str, Any] | None = None,
        order_by: list[dict[str, str]] | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> TokenFlowsResponse:
        """Get aggregated per-wallet-category flow data for a single token in a date window.

        Stablecoins are not supported on this endpoint -- returns 404.

        Args:
            symbol: Token identifier (CoinGecko ID preferred, e.g. ``"uniswap"``).
                Stablecoins are rejected.
            chain: Blockchain (default: "ethereum").
            date_from: Start date YYYY-MM-DD. Default: 7 days ago.
            date_to: End date YYYY-MM-DD. Default: today.
            label: Wallet category to scope to -- one of ``"smart_money"``,
                ``"exchange"``, ``"whale"``, ``"public_figure"``, ``"top_100_holders"``.
            filters: Nansen filter dict.
            order_by: Sort order.
            page: Page number.
            per_page: Page size.
        """
        body: dict[str, Any] = {"page": page, "per_page": per_page}
        if chain is not None:
            body["chain"] = chain
        if date_from is not None or date_to is not None:
            body["date_range"] = {
                k: v for k, v in {"from": date_from, "to": date_to}.items() if v is not None
            }
        if label is not None:
            body["label"] = label
        if filters is not None:
            body["filters"] = filters
        if order_by is not None:
            body["order_by"] = order_by
        return self._request_model(
            "POST",
            f"/on-chain/token/{symbol}/flows",
            TokenFlowsResponse,
            json=body,
        )

    def get_onchain_series(
        self,
        symbol: str,
        metrics: list[str],
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        interval: str = "1h",
        chain: str | None = None,
        provider: str | None = None,
        top_n: int = 10,
    ) -> OnChainSeriesResponse:
        """Per-bar on-chain metric series for a token (one column per metric).

        The same call serves a live trailing window (e.g. the last 10 days, ending now)
        or a long historical range -- it is just a different ``date_from``. Build a
        DataFrame with ``pd.DataFrame(resp.series).set_index("timestamp")``.

        Args:
            symbol: Token identifier (e.g. ``"WETH"``).
            metrics: Subset of ``"SmartMoneyNetflow"``, ``"SmartMoneyHoldings"``,
                ``"ExchangeNetflow"``, ``"WhaleNetInflow"``, ``"HolderConcentration"``.
            date_from: Start date YYYY-MM-DD. Default: 10 days ago.
            date_to: End date YYYY-MM-DD. Default: today.
            interval: Resample interval -- ``"1h"`` (default), ``"4h"``, ``"1d"``, ``"1w"``.
            chain: Blockchain (default: "ethereum").
            provider: ``None``/``"nansen"`` (default, uncapped) or ``"whalealert"``
                (30-day fallback, ExchangeNetflow/WhaleNetInflow only).
            top_n: Top-N holders summed for HolderConcentration. Default: 10.
        """
        body: dict[str, Any] = {"symbol": symbol, "metrics": metrics,
                                "interval": interval, "top_n": top_n}
        if chain is not None:
            body["chain"] = chain
        if provider is not None:
            body["provider"] = provider
        if date_from is not None or date_to is not None:
            body["date_range"] = {
                k: v for k, v in {"from": date_from, "to": date_to}.items() if v is not None
            }
        return self._request_model(
            "POST",
            "/on-chain/series",
            OnChainSeriesResponse,
            json=body,
        )
