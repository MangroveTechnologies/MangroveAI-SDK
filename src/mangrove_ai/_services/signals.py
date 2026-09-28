from __future__ import annotations

import builtins
from collections.abc import Iterator
from typing import Any

from pydantic import ValidationError as ModelValidationError

from .._pagination import PaginatedResponse, paginate_iter
from ..exceptions import MalformedResponseError
from ..models.signals import (
    EvaluateResponse,
    MatchResponse,
    SearchSignalsRequest,
    Signal,
    SignalBehaviorResult,
    SignalListPage,
    ValidationResponse,
)
from ._base import BaseService


class SignalsService(BaseService):
    """Signal discovery, evaluation, and validation."""

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        category: str | None = None,
        regime_direction: str | None = None,
        role: str | None = None,
    ) -> SignalListPage:
        """List available trading signals.

        Filters combine: a signal is returned only if it satisfies every filter
        supplied. The server owns the accepted values and rejects an unknown one
        rather than ignoring it, so the values named below are a guide to what is
        currently accepted, not a list this client enforces.

        Args:
            limit: Page size requested. The server applies its own ceiling and may
                serve fewer rows than asked for. Use ``next_offset`` from the result
                to continue, or ``list_iter`` to page automatically.
            offset: Index of the first record to return.
            category: Signal library module, e.g. "momentum", "trend", "volume",
                "volatility", "patterns", "onchain".
            regime_direction: Market regime band to narrow to, e.g. "bull", "bear",
                "neutral", as reported by a market regime lookup. Keeps only signals
                admissible for that regime.
            role: The part a signal plays in a strategy -- "TRIGGER" or "FILTER".

        Raises:
            ValidationError: A page bound or filter value the server does not accept.
            ServiceUnavailableError: The signal catalogue is not loaded. Distinct
                from an empty result, which is a successful answer.
            MalformedResponseError: The response contains invalid signal or page data.
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        for name, value in (
            ("category", category),
            ("regime_direction", regime_direction),
            ("role", role),
        ):
            if value is not None:
                params[name] = value

        data = self._request("GET", "/signals/", params=params)
        if not isinstance(data, dict) or not isinstance(data.get("signals"), builtins.list):
            raise MalformedResponseError(
                "Signal listing response must contain a 'signals' list."
            )

        page: dict[str, Any] = {
            "items": data["signals"],
            "total": data.get("total", len(data["signals"])),
            "offset": data.get("offset", offset),
            "limit": data.get("limit", limit),
            "filter": data.get("filter"),
        }
        # Passed on only where the server reported them, so an endpoint that does not
        # is left to the page's own derivation rather than told "no further results".
        for key in ("has_more", "next_offset"):
            if data.get(key) is not None:
                page[key] = data[key]
        try:
            return SignalListPage(**page)
        except ModelValidationError:
            # Pydantic errors include rejected input values; do not expose those
            # through the traceback of the public SDK error.
            raise MalformedResponseError(
                "Signal listing response contains invalid signal or page data."
            ) from None

    def list_iter(
        self,
        *,
        limit_per_page: int = 50,
        category: str | None = None,
        regime_direction: str | None = None,
        role: str | None = None,
    ) -> Iterator[Signal]:
        """Auto-paginating iterator over every signal matching the filters.

        Each page is continued from the offset the server reports, so a page
        ceiling below ``limit_per_page`` yields every record rather than skipping
        the rows between the size requested and the size served.
        Each fetched page is a separate billable request. Use ``list`` when you
        want exactly one page.
        """
        return paginate_iter(
            lambda offset, limit: self.list(
                limit=limit,
                offset=offset,
                category=category,
                regime_direction=regime_direction,
                role=role,
            ),
            limit_per_page=limit_per_page,
        )

    def get(self, signal_name: str) -> Signal:
        """Get full metadata for a signal by name."""
        data = self._request("GET", f"/signals/{signal_name}")
        return Signal.model_validate(data)

    def search(self, request: SearchSignalsRequest) -> PaginatedResponse[Signal]:
        """Search signals by name, params, or keywords.

        Args:
            request: Search query with search_type (name, params, keywords).
        """
        data = self._request("POST", "/signals/search", json=request.model_dump())
        items = [Signal.model_validate(s) for s in data["signals"]]
        return PaginatedResponse(
            items=items,
            total=data.get("total", len(items)),
            offset=data.get("offset", request.offset),
            limit=data.get("limit", request.limit),
        )

    def match(
        self,
        description: str,
        *,
        top_k: int = 5,
        similarity_threshold: float = 0.5,
    ) -> MatchResponse:
        """Find signals matching a natural language description.

        Args:
            description: What the signal should do.
            top_k: Max number of matches to return.
            similarity_threshold: Minimum similarity score (0-1).
        """
        data = self._request("POST", "/signals/match", json={
            "description": description,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
        })
        return MatchResponse.model_validate(data)

    def evaluate(
        self,
        signal_name: str,
        market_data: list[dict[str, Any]],
        parameters: dict[str, Any],
    ) -> EvaluateResponse:
        """Evaluate a signal against market data.

        Args:
            signal_name: Signal function name.
            market_data: OHLCV data points.
            parameters: Signal-specific parameters.
        """
        data = self._request("POST", f"/signals/{signal_name}/evaluate", json={
            "market_data": market_data,
            "parameters": parameters,
        })
        return EvaluateResponse.model_validate(data)

    def validate(
        self,
        code: str,
        params: dict[str, Any],
        description: str,
    ) -> ValidationResponse:
        """Validate signal code, parameters, and metadata.

        Args:
            code: Python function code for the signal.
            params: Parameter specifications.
            description: Signal description.
        """
        data = self._request("POST", "/signals/validate", json={
            "code": code,
            "params": params,
            "description": description,
        })
        return ValidationResponse.model_validate(data)

    def query_signal_behavior(
        self,
        lookup: str,
        *,
        signal_type: str = "FILTER",
        signal: str | None = None,
        target_rate: float | None = None,
        min_rate: float | None = None,
        max_rate: float | None = None,
        min_run_bars: float | None = None,
        max_run_bars: float | None = None,
        min_gap_bars: float | None = None,
        max_gap_bars: float | None = None,
        min_gap_range_bars: float | None = None,
        max_gap_range_bars: float | None = None,
        category: str | None = None,
        limit: int = 10,
    ) -> SignalBehaviorResult:
        """What a signal was MEASURED to do on a real chart, across its parameter range.

        A FILTER is an ongoing state, measured for how OFTEN it is true (selectivity,
        a fraction 0-1) and how LONG it stays true. A TRIGGER marks one bar, measured
        for its activity (firings per 1,000 bars) and reactivity (the gaps between
        firings). Mirrors the copilot's ``query_signal_behavior`` tool
        (``POST /signals/behavior``).

        Args:
            lookup: ``describe`` (one signal's parameters, span and default),
                ``pick`` (settings of one signal near ``target_rate``), ``find``
                (signals reaching ``min_rate``..``max_rate``) or ``gap_probability``
                (share of a signal's gaps within ``min_gap_range_bars``..
                ``max_gap_range_bars``, per configuration).
            signal_type: ``FILTER`` or ``TRIGGER``.
            signal: Signal name. Required by describe, pick and gap_probability.
            target_rate: pick -- FILTER selectivity 0-1, or TRIGGER firings per 1,000 bars.
            min_rate: find -- low end of the band, same units (required for find).
            max_rate: find -- high end of the band, same units (required for find).
            min_run_bars: pick/find, FILTER only -- mean run at least this many bars.
            max_run_bars: pick/find, FILTER only -- mean run at most this many bars.
            min_gap_bars: pick/find, TRIGGER only -- median gap at least this many bars.
            max_gap_bars: pick/find, TRIGGER only -- median gap at most this many bars.
            min_gap_range_bars: gap_probability -- low end of the gap range, inclusive.
            max_gap_range_bars: gap_probability -- high end of the gap range, inclusive.
            category: find -- restrict to one family, e.g. ``oscillator``.
            limit: Maximum results, 1-100.

        Raises:
            ValidationError: A missing or malformed argument, an unknown lookup, or
                (describe) an unknown signal name.
        """
        body: dict[str, Any] = {"lookup": lookup, "signal_type": signal_type}
        for key, value in (
            ("signal", signal),
            ("target_rate", target_rate),
            ("min_rate", min_rate),
            ("max_rate", max_rate),
            ("min_run_bars", min_run_bars),
            ("max_run_bars", max_run_bars),
            ("min_gap_bars", min_gap_bars),
            ("max_gap_bars", max_gap_bars),
            ("min_gap_range_bars", min_gap_range_bars),
            ("max_gap_range_bars", max_gap_range_bars),
            ("category", category),
        ):
            if value is not None:
                body[key] = value
        body["limit"] = limit
        return self._request_model("POST", "/signals/behavior", SignalBehaviorResult, json=body)
