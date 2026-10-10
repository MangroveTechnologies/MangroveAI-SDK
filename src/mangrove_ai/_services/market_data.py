"""Market-data service -- regime readings (``/api/v1/market-data/*``).

Both methods are billable (one ``api_calls`` unit per successful call; 4xx responses
are not billed) and require an API key.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import quote

from ..models.market_data import MarketRegime, MarketSegment
from ._base import BaseService


class MarketDataService(BaseService):
    """Regime classification: an asset's current regime, or one named stretch of the past."""

    def get_market_regime(self, asset: str, *, lookback_days: int | None = None) -> MarketRegime:
        """Classify an asset's current regime from up to 12 months of daily closes.

        The return and a bull/neutral/bear band over 90, 180 and 365 days, plus
        annualised volatility with a low/medium/high bucket and a z-score against the
        asset's own baseline, and the whole lookback in the sweep catalog's labels
        (``window``). Mirrors the copilot's ``get_market_regime`` tool.

        Covers crypto and the stocks, ETFs, commodities and bonds in Oracle's regime
        catalog: SPY, QQQ, DIA, IWM, AAPL, AMD, AMZN, COST, GOOGL, HD, JNJ, JPM, META,
        MSFT, NFLX, NVDA, PG, TSLA, UNH, WMT, XOM, GLD, SLV, USO, ``"GOLD"`` (gold
        futures), ``"CRUDE"`` (crude oil futures) and TLT. Those tickers are read from
        their exchange-session daily series, even where a crypto token shares one; any
        other ticker is read as crypto, so a stock not named here cannot be read. A
        listed ticker needs at least 15 sessions with a close, about three weeks.
        ``venue`` says which feed was read.

        Args:
            asset: Asset symbol, e.g. ``"BTC"``, ``"SPY"``, ``"GOLD"`` or ``"CRUDE"``.
            lookback_days: Days of daily closes to read, 1-365 (server default 365).
                For a stock, ETF, commodity or bond these are calendar days, so 365
                reads about 250 sessions.

        Returns:
            ``MarketRegime`` -- ``asset``, ``venue``, ``bars`` and ``regime`` (``asof``,
            ``direction`` keyed ``"90d"``/``"180d"``/``"365d"``, ``volatility``,
            ``window``). Percent fields are on a 0-100 scale.

        Raises:
            ValidationError: Bad ``lookback_days`` (400) or too little history (422).
            NotFoundError: No price data for the asset.
        """
        params: dict[str, Any] = {}
        if lookback_days is not None:
            params["lookback_days"] = lookback_days
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
    ) -> MarketSegment:
        """Classify one stretch of market in the sweep catalog's labels.

        Supply ``window_file`` (a catalog window's file name), OR ``asset`` with both
        dates -- not both. Returns the direction band, volatility band (``unscored``
        when no fitted band covers the stretch's length; ``scale_bands`` says which
        lengths have one), trend character, era, the features behind them and the
        ``venue`` read. For an asset's CURRENT conditions use :meth:`get_market_regime`.
        Mirrors the copilot's ``classify_market_segment`` tool.

        Covers crypto and the stocks, ETFs, commodities and bonds in Oracle's regime
        catalog: SPY, QQQ, DIA, IWM, AAPL, AMD, AMZN, COST, GOOGL, HD, JNJ, JPM, META,
        MSFT, NFLX, NVDA, PG, TSLA, UNH, WMT, XOM, GLD, SLV, USO, ``"GOLD"`` (gold
        futures), ``"CRUDE"`` (crude oil futures) and TLT. Those tickers are read from
        their exchange-session daily series, even where a crypto token shares one; any
        other ticker is read as crypto, so a stock not named here cannot be read. A
        listed ticker needs at least 15 sessions with a close, about three weeks.

        Args:
            asset: Asset symbol, e.g. ``"BTC"``, ``"SPY"``, ``"GOLD"`` or ``"CRUDE"``.
            start_date: ISO start of the stretch, e.g. ``"2026-01-01"``.
            end_date: ISO end of the stretch, inclusive.
            candle_size: Explicit ranges support ``"1d"``; catalogue windows retain their stored interval.
            window_file: A sweep-catalog window's file name.

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
            )
            if value is not None
        }
        return self._request_model("GET", "/market-data/segment", MarketSegment, params=params)
