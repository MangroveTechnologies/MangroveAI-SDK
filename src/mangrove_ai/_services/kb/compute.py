from __future__ import annotations

from typing import Any

from ...models.kb import KBComputeResult
from .._base import BaseService


class KBComputeService(BaseService):
    """KB x402 payment-gated computation endpoints."""

    def evaluate_signal(
        self,
        name: str,
        ohlcv: list[dict[str, Any]],
        params: dict[str, Any] | None = None,
    ) -> KBComputeResult:
        """Evaluate a signal against OHLCV data (x402 paid).

        Args:
            name: Signal function name.
            ohlcv: OHLCV candlestick data.
            params: Signal-specific parameters.
        """
        body: dict[str, Any] = {"name": name, "ohlcv": ohlcv}
        if params:
            body["params"] = params
        return self._request_model("POST", "/evaluate", KBComputeResult, json=body)

    def compute_indicator(
        self,
        name: str,
        data: dict[str, list[float]],
        params: dict[str, Any] | None = None,
    ) -> KBComputeResult:
        """Compute an indicator (x402 paid).

        Args:
            name: Indicator function name.
            data: Input data series (e.g. {"close": [...], "volume": [...]}).
            params: Indicator-specific parameters.
        """
        body: dict[str, Any] = {"name": name, "data": data}
        if params:
            body["params"] = params
        return self._request_model("POST", "/compute", KBComputeResult, json=body)
