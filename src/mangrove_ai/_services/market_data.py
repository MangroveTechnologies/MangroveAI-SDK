"""Authenticated market-data reads (``/api/v1/market-data/*``).

Methods do not paginate or start collection. The client HTTP retry policy still
applies; use ``auto_retry=False`` for one transport attempt.
"""
from __future__ import annotations

from typing import Any, cast
from urllib.parse import quote

from ..models.market_data import MarketRegime, MarketSegment
from ._base import BaseService


class MarketDataService(BaseService):
    """Market regimes, bounded order books and trades, and venue liquidation levels."""

    def get_orderbook(
        self, symbol_id: str, *, limit_levels: int = 20, provider: str = "coinapi",
    ) -> dict[str, Any]:
        """Read one CoinAPI order-book snapshot, including the best bid and ask.

        ``symbol_id`` is an exact spot instrument, such as ``COINBASE_SPOT_BTC_USD``.
        The server accepts 1-200 levels per side. Prices and notional values use
        that instrument's quote currency; sizes use its base currency. This is
        one bounded read, not a stream or a history collection job.
        """
        return cast(dict[str, Any], self._request("GET", "/market-data/orderbook", params={
            "symbol_id": symbol_id, "limit_levels": limit_levels, "provider": provider,
        }))

    def get_orderbook_history(
        self, symbol_id: str, time_start: str, time_end: str, *,
        limit: int = 100, limit_levels: int = 20, provider: str = "coinapi",
    ) -> dict[str, Any]:
        """Read a bounded CoinAPI order-book history response.

        Supply timezone-aware ISO timestamps spanning at most 24 hours. The
        server accepts 1-1,000 snapshots and 1-50 levels per side. Preserve the
        response's coverage and limit metadata when comparing bid buildup;
        returned snapshots do not establish complete order-by-order history.
        No additional pages are fetched automatically.
        """
        return cast(dict[str, Any], self._request("GET", "/market-data/orderbook/history", params={
            "symbol_id": symbol_id, "time_start": time_start, "time_end": time_end,
            "limit": limit, "limit_levels": limit_levels, "provider": provider,
        }))

    def get_order_flow(
        self, symbol_id: str, time_start: str, time_end: str, *,
        limit: int = 100, provider: str = "coinapi",
    ) -> dict[str, Any]:
        """Read trades and their server-calculated aggressive buy/sell imbalance.

        Supply timezone-aware ISO timestamps spanning at most 24 hours and a
        limit of 1-1,000 trades. Delta and cumulative volume delta describe only
        the returned trades, in the instrument's quote currency. Unknown taker
        sides stay unknown. Trades cannot reconstruct resting order-book depth.
        """
        return cast(dict[str, Any], self._request("GET", "/market-data/order-flow", params={
            "symbol_id": symbol_id, "time_start": time_start, "time_end": time_end,
            "limit": limit, "provider": provider,
        }))

    def get_liquidation_levels(
        self, token_symbol: str = "BTC", *, page: int = 1,
        per_page: int = 100, provider: str = "nansen",
    ) -> dict[str, Any]:
        """Read one Nansen page of reported Hyperliquid position thresholds.

        The server accepts page 1-10,000 and page size 1-100. The response retains
        missing liquidation prices as null and reports its venue and coverage.
        These are current position liquidation levels, not realized liquidations
        or an estimate covering all exchanges. Each page is a separate explicit
        request; the SDK never fetches another page automatically.
        """
        return cast(dict[str, Any], self._request("GET", "/market-data/liquidation-levels", params={
            "token_symbol": token_symbol, "page": page,
            "per_page": per_page, "provider": provider,
        }))

    def get_market_regime(
        self, asset: str, *, lookback_days: int | None = None,
        provider: str | None = None, quote_token: str | None = None,
        market_data_venue: str | None = None,
    ) -> MarketRegime:
        """Classify an asset's current regime from up to 12 months of daily closes.

        The return and a bull/neutral/bear band over 90, 180 and 365 days, plus
        annualised volatility with a low/medium/high bucket and a z-score against the
        asset's own baseline, and the whole lookback in the sweep catalog's labels
        (``window``). Mirrors the copilot's ``get_market_regime`` tool.

        Covers crypto and the stocks, ETFs, commodities and bonds in Oracle's regime
        catalog: SPY, QQQ, DIA, IWM, AAPL, AMD, AMZN, COST, GOOGL, HD, JNJ, JPM, META,
        MSFT, NFLX, NVDA, PG, TSLA, UNH, WMT, XOM, GLD, SLV, USO, ``"GOLD"`` (gold
        futures), ``"CRUDE"`` (crude oil futures) and TLT. Without explicit source
        arguments, those tickers are read from
        their exchange-session daily series, even where a crypto token shares one; any
        other ticker is read as crypto, so a stock not named here cannot be read. A
        listed ticker needs at least 15 sessions with a close, about three weeks.
        Explicit market or provider arguments select the crypto history path.
        ``venue`` says which feed was read.

        Args:
            asset: Asset symbol, e.g. ``"BTC"``, ``"SPY"``, ``"GOLD"`` or ``"CRUDE"``.
            lookback_days: Days of daily closes to read, 1-365 (server default 365).
                For a stock, ETF, commodity or bond these are calendar days, so 365
                reads about 250 sessions.
            provider: Explicit external history source.
            quote_token: Quote currency; supply with market_data_venue.
            market_data_venue: Exact exchange; supply with quote_token.

        Returns:
            ``MarketRegime`` -- ``asset``, ``venue``, ``bars`` and ``regime`` (``asof``,
            ``direction`` keyed ``"90d"``/``"180d"``/``"365d"``, ``volatility``,
            ``window``). Percent fields are on a 0-100 scale.

        Raises:
            ValidationError: Bad ``lookback_days`` (400) or too little history (422).
            NotFoundError: No price data for the asset.
        """
        params: dict[str, Any] = {}
        for key, value in (("lookback_days", lookback_days), ("provider", provider),
                           ("quote_token", quote_token), ("market_data_venue", market_data_venue)):
            if value is not None:
                params[key] = value
        return self._request_model(
            "GET", f"/market-data/regime/{quote(asset, safe='')}", MarketRegime, params=params or None
        )

    def classify_market_segment(
        self,
        *,
        asset: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        candle_size: str | None = None,
        window_file: str | None = None,
        provider: str | None = None,
        quote_token: str | None = None,
        market_data_venue: str | None = None,
    ) -> MarketSegment:
        """Classify one stretch of market in the sweep catalog's labels.

        Supply ``window_file`` (a catalog window's file name), OR ``asset`` with both
        dates -- not both. Returns the direction band, volatility band (``unscored``
        when no fitted band covers the stretch's length; ``scale_bands`` says which
        lengths have one), trend character, the features behind them and the
        ``venue`` read. For an asset's CURRENT conditions use :meth:`get_market_regime`.
        Mirrors the copilot's ``classify_market_segment`` tool.

        Covers crypto and the stocks, ETFs, commodities and bonds in Oracle's regime
        catalog: SPY, QQQ, DIA, IWM, AAPL, AMD, AMZN, COST, GOOGL, HD, JNJ, JPM, META,
        MSFT, NFLX, NVDA, PG, TSLA, UNH, WMT, XOM, GLD, SLV, USO, ``"GOLD"`` (gold
        futures), ``"CRUDE"`` (crude oil futures) and TLT. Without explicit source
        arguments, those tickers are read from
        their exchange-session daily series, even where a crypto token shares one; any
        other ticker is read as crypto, so a stock not named here cannot be read. A
        listed ticker needs at least 15 sessions with a close, about three weeks.
        Explicit market or provider arguments select the crypto history path.

        Args:
            asset: Asset symbol, e.g. ``"BTC"``, ``"SPY"``, ``"GOLD"`` or ``"CRUDE"``.
            start_date: ISO start of the stretch, e.g. ``"2026-01-01"``.
            end_date: ISO end of the stretch, inclusive.
            candle_size: Explicit ranges support ``"1d"``; catalogue windows retain their stored interval.
            window_file: A sweep-catalog window's file name.
            provider: Explicit external source for date-based history.
            quote_token: Quote currency for date-based history.
            market_data_venue: Exact exchange; supply with quote_token.

        Raises:
            ValidationError: Neither/both of window and range, a malformed or inverted
                range (400), or too little history (422).
            NotFoundError: No price data, or no such window.
        """
        params = {
            key: value
            for key, value in (
                ("asset", asset),
                ("start_date", start_date),
                ("end_date", end_date),
                ("candle_size", candle_size),
                ("window_file", window_file),
                ("provider", provider),
                ("quote_token", quote_token),
                ("market_data_venue", market_data_venue),
            )
            if value is not None
        }
        return self._request_model("GET", "/market-data/segment", MarketSegment, params=params)
