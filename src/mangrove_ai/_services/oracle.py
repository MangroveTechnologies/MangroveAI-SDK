"""MangroveOracle endpoints reached through MangroveAI's reverse proxy.

All methods POST to ``/oracle/<path>`` via the core (v1) transport. The
upstream Oracle service handles the actual SIEVE scoring, BigQuery query
serving, and backtest engine. This service is a thin typed wrapper.
"""
from __future__ import annotations

from typing import Any

from .._transport._service import ServiceTransport
from ..models.oracle import (
    DataQueryRequest,
    DataQueryResponse,
    OracleAsyncBacktestStatus,
    OracleAsyncBacktestSubmission,
    OracleBacktestRequest,
    OracleBacktestResult,
    OracleBulkBacktestRequest,
    OracleBulkBacktestResult,
    SieveScoreRequest,
    SieveScoreResponse,
)


SIEVE_MAX_ITEMS_PER_REQUEST = 99


class OracleService:
    """Score strategies through SIEVE, query the corpus, or run backtests."""

    def __init__(self, core_transport: ServiceTransport, v2_transport: ServiceTransport) -> None:
        self._core = core_transport
        # v2 transport currently unused but kept for parity with BacktestingService —
        # future Oracle endpoints (e.g. streaming SSE for sweep progress) may use it.
        self._v2 = v2_transport

    def _core_request(self, method: str, path: str, **kwargs: Any) -> dict:
        response = self._core.request(method, path, **kwargs)
        return response.json()

    # ------------------------------------------------------------------ #
    # SIEVE
    # ------------------------------------------------------------------ #
    def sieve_score(self, request: SieveScoreRequest) -> SieveScoreResponse:
        """Score up to 99 strategies through the Mangrove SIEVE classifier.

        Returns binary go/no-go probabilities and 4-class outcome
        probabilities per item, plus ``model_version`` and ``code_version``
        for provenance.

        Args:
            request: ``SieveScoreRequest`` with exactly one of
                ``strategies`` (MangroveAI-shaped Strategy objects) or
                ``runs`` (raw run dicts) set. Maximum 99 items per request.

        Raises:
            ValueError: when more than 99 items are supplied or when both
                / neither input field is set (caught client-side before the
                request is sent, mirroring the server's HTTP 413 / 400).
        """
        payload = request.model_dump(exclude_none=True)
        has_strategies = bool(payload.get("strategies"))
        has_runs = bool(payload.get("runs"))
        if has_strategies == has_runs:
            raise ValueError(
                "Provide exactly one of `strategies` or `runs` (and not an empty list)"
            )
        item_count = len(payload.get("strategies") or payload.get("runs") or [])
        if item_count > SIEVE_MAX_ITEMS_PER_REQUEST:
            raise ValueError(
                f"Max {SIEVE_MAX_ITEMS_PER_REQUEST} items per request, got {item_count}"
            )

        data = self._core_request("POST", "/oracle/sieve/score", json=payload)
        return SieveScoreResponse.model_validate(data)

    # ------------------------------------------------------------------ #
    # Data query (BigQuery proxy)
    # ------------------------------------------------------------------ #
    def data_query(self, request: DataQueryRequest) -> DataQueryResponse:
        """Run a curated query against the Oracle corpus (results / ohlcv).

        Columns and filter operators are whitelisted server-side.
        """
        data = self._core_request(
            "POST", "/oracle/data/query", json=request.model_dump(exclude_none=True)
        )
        return DataQueryResponse.model_validate(data)

    # ------------------------------------------------------------------ #
    # Backtests
    # ------------------------------------------------------------------ #
    def backtest(self, request: OracleBacktestRequest) -> OracleBacktestResult:
        """Run a single-strategy backtest synchronously."""
        data = self._core_request(
            "POST", "/oracle/backtest", json=request.model_dump(exclude_none=True)
        )
        return OracleBacktestResult.model_validate(data)

    def backtest_async(
        self, request: OracleBacktestRequest
    ) -> OracleAsyncBacktestSubmission:
        """Submit a backtest for async execution; returns a backtest_id."""
        data = self._core_request(
            "POST", "/oracle/backtest/async", json=request.model_dump(exclude_none=True)
        )
        return OracleAsyncBacktestSubmission.model_validate(data)

    def backtest_poll(self, backtest_id: str) -> OracleAsyncBacktestStatus:
        """Poll the status / result of an async backtest by ID."""
        data = self._core_request("GET", f"/oracle/backtest/async/{backtest_id}/status")
        return OracleAsyncBacktestStatus.model_validate(data)

    def backtest_bulk(
        self, request: OracleBulkBacktestRequest
    ) -> OracleBulkBacktestResult:
        """Evaluate many strategies over a shared date range in one call."""
        data = self._core_request(
            "POST", "/oracle/backtest/bulk", json=request.model_dump(exclude_none=True)
        )
        return OracleBulkBacktestResult.model_validate(data)
