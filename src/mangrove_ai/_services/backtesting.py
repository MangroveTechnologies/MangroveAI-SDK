from __future__ import annotations

import time

from .._transport._service import ServiceTransport
from ..exceptions import TimeoutError
from ..models.backtesting import (
    AsyncBacktestStatus,
    AsyncBacktestSubmission,
    BacktestRequest,
    BacktestResult,
    BacktestTradesResponse,
    BulkBacktestRequest,
    BulkBacktestResult,
)


class BacktestingService:
    """Backtest execution and result retrieval."""

    def __init__(self, core_transport: ServiceTransport, v2_transport: ServiceTransport) -> None:
        self._core = core_transport
        self._v2 = v2_transport

    def _core_request(self, method: str, path: str, **kwargs) -> dict:
        response = self._core.request(method, path, **kwargs)
        return response.json()

    def _v2_request(self, method: str, path: str, **kwargs) -> dict:
        response = self._v2.request(method, path, **kwargs)
        return response.json()

    def run(self, request: BacktestRequest) -> BacktestResult:
        """Run a synchronous single-strategy backtest.

        Args:
            request: Backtest configuration including asset, interval, strategy, and risk params.
        """
        data = self._core_request("POST", "/backtesting/backtest", json=request.model_dump(exclude_none=True))
        return BacktestResult.model_validate(data)

    def run_bulk(self, request: BulkBacktestRequest) -> BulkBacktestResult:
        """Run multiple strategies over a shared date range.

        Args:
            request: Bulk backtest configuration with strategy_ids or strategy_configs.
        """
        data = self._core_request("POST", "/backtesting/backtest/bulk", json=request.model_dump(exclude_none=True))
        return BulkBacktestResult.model_validate(data)

    def get(self, backtest_id: str) -> BacktestResult:
        """Get a backtest result by ID."""
        data = self._core_request("GET", f"/backtesting/backtest/{backtest_id}")
        return BacktestResult.model_validate(data)

    def get_trades(self, backtest_id: str) -> BacktestTradesResponse:
        """Get trade history for a backtest."""
        data = self._core_request("GET", f"/backtesting/backtest/{backtest_id}/trades")
        return BacktestTradesResponse.model_validate(data)

    def submit_async(self, request: BacktestRequest) -> AsyncBacktestSubmission:
        """Submit a backtest for async execution.

        Args:
            request: Backtest configuration (same as run()).

        Returns:
            Submission with backtest_id and initial status.
        """
        data = self._v2_request("POST", "/backtests/", json=request.model_dump(exclude_none=True))
        return AsyncBacktestSubmission.model_validate(data)

    def poll_status(self, backtest_id: str) -> AsyncBacktestStatus:
        """Check the status of an async backtest."""
        data = self._v2_request("GET", f"/backtests/{backtest_id}/status")
        return AsyncBacktestStatus.model_validate(data)

    def run_async(
        self,
        request: BacktestRequest,
        *,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
    ) -> BacktestResult:
        """Submit a backtest, poll until complete, and return the result.

        Args:
            request: Backtest configuration.
            poll_interval: Seconds between status checks.
            timeout: Maximum seconds to wait before raising TimeoutError.
        """
        submission = self.submit_async(request)
        backtest_id = submission.backtest_id
        start = time.monotonic()

        while True:
            elapsed = time.monotonic() - start
            if elapsed > timeout:
                raise TimeoutError(
                    f"Async backtest {backtest_id} did not complete within {timeout}s"
                )

            status = self.poll_status(backtest_id)

            if status.status == "completed":
                return BacktestResult(
                    success=True,
                    metrics=status.metrics,
                    trade_history=status.trade_history,
                    execution_time_seconds=status.execution_time_seconds,
                    trade_count=len(status.trade_history) if status.trade_history else 0,
                )

            if status.status == "failed":
                return BacktestResult(
                    success=False,
                    error=status.error_message,
                    execution_time_seconds=status.execution_time_seconds,
                )

            time.sleep(poll_interval)
