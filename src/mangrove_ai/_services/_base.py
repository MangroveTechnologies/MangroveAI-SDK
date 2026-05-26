from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from .._transport._service import ServiceTransport

T = TypeVar("T", bound=BaseModel)


class BaseService:
    """Base class for all sync service implementations."""

    _service: str = "core"

    def __init__(self, transport: ServiceTransport) -> None:
        self._transport = transport

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> Any:
        response = self._transport.request(method, path, params=params, json=json)
        return response.json()

    def _request_model(
        self,
        method: str,
        path: str,
        model: type[T],
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        key: str | None = None,
    ) -> T:
        data = self._request(method, path, params=params, json=json)
        if key is not None:
            data = data[key]
        return model.model_validate(data)

    def _request_list(
        self,
        method: str,
        path: str,
        model: type[T],
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        key: str,
    ) -> list[T]:
        data = self._request(method, path, params=params, json=json)
        return [model.model_validate(item) for item in data[key]]
