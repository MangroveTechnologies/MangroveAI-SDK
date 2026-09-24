from __future__ import annotations

import json as json_mod
from typing import Any

import pytest
from pydantic import BaseModel

from mangrove_ai import MangroveAI
from mangrove_ai._pagination import PaginatedResponse, paginate_iter
from mangrove_ai._transport._mock import MockTransport, RecordedRequest
from mangrove_ai._transport._protocol import TransportResponse
from mangrove_ai.exceptions import MalformedResponseError

CLAMP = "clamp"
FALL_BACK = "fall_back"


class _RecordingTransport(MockTransport):
    """Base for transports that compute a response instead of replaying a canned one."""

    def _body(self, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        timeout: float | None = None,
    ) -> TransportResponse:
        params = params or {}
        self.requests.append(
            RecordedRequest(
                method=method.upper(), url=url, headers=headers, params=params, json=json
            )
        )
        body = self._body(params)
        return TransportResponse(
            status_code=200, headers={}, data=body, text=json_mod.dumps(body)
        )


class CatalogueTransport(_RecordingTransport):
    """Serves a fixed catalogue under a server-side page rule.

    The size a caller requests and the size a server serves are separate numbers:
    the server applies its own default and ceiling. Reproducing that is the point of
    the fixture -- a transport that always returns exactly the size requested cannot
    detect a client that assumes it will.
    """

    def __init__(
        self,
        catalogue_size: int,
        *,
        default: int,
        maximum: int,
        oversize: str = CLAMP,
    ) -> None:
        super().__init__()
        self._records = [
            {"name": f"signal_{i:03d}", "category": "momentum"}
            for i in range(catalogue_size)
        ]
        self._default = default
        self._maximum = maximum
        self._oversize = oversize

    def _page_size(self, requested: Any) -> int:
        if requested is None:
            return self._default
        requested = int(requested)
        if requested <= self._maximum:
            return requested
        return self._maximum if self._oversize == CLAMP else self._default

    def _body(self, params: dict[str, Any]) -> dict[str, Any]:
        offset = int(params.get("offset", 0))
        served = self._page_size(params.get("limit"))
        rows = self._records[offset : offset + served]
        page_end = offset + len(rows)
        has_more = page_end < len(self._records)
        return {
            "signals": rows,
            "total": len(self._records),
            "limit": served,
            "offset": offset,
            "has_more": has_more,
            "next_offset": page_end if has_more else None,
        }


class StuckTransport(_RecordingTransport):
    """Reports further results while pointing back at the page just served."""

    def __init__(self, *, rows: int, next_offset: int) -> None:
        super().__init__()
        self._rows = rows
        self._next_offset = next_offset

    def _body(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "signals": [
                {"name": f"signal_{i}", "category": "momentum"} for i in range(self._rows)
            ],
            "total": 500,
            "limit": 50,
            "offset": 0,
            "has_more": True,
            "next_offset": self._next_offset,
        }


def _client(transport: MockTransport) -> MangroveAI:
    return MangroveAI(api_key="test_abc123", environment="local", httpx_client=transport)


class Record(BaseModel):
    name: str


def _page(**kwargs: Any) -> PaginatedResponse[Record]:
    return PaginatedResponse[Record](**kwargs)


class TestIterationCoversTheCatalogue:
    def test_every_record_arrives_when_the_server_serves_a_smaller_page(self) -> None:
        transport = CatalogueTransport(96, default=30, maximum=30)

        names = [s.name for s in _client(transport).signals.list_iter(limit_per_page=50)]

        assert names == [f"signal_{i:03d}" for i in range(96)]

    @pytest.mark.parametrize("catalogue_size", [30, 50, 96, 100, 101, 300])
    def test_every_record_arrives_when_the_server_falls_back_below_the_request(
        self, catalogue_size: int,
    ) -> None:
        transport = CatalogueTransport(catalogue_size, default=50, maximum=100, oversize=FALL_BACK)

        names = [s.name for s in _client(transport).signals.list_iter(limit_per_page=200)]

        assert names == [f"signal_{i:03d}" for i in range(catalogue_size)]

    def test_filters_are_preserved_on_every_page(self) -> None:
        transport = CatalogueTransport(96, default=30, maximum=30)

        list(_client(transport).signals.list_iter(
            category="momentum", regime_direction="bear", role="FILTER"
        ))

        assert len(transport.requests) == 4
        for request in transport.requests:
            assert request.params["category"] == "momentum"
            assert request.params["regime_direction"] == "bear"
            assert request.params["role"] == "FILTER"

    def test_no_record_is_yielded_twice(self) -> None:
        transport = CatalogueTransport(96, default=30, maximum=30)

        names = [s.name for s in _client(transport).signals.list_iter(limit_per_page=50)]

        assert len(names) == len(set(names))

    def test_offsets_follow_the_size_served_not_the_size_requested(self) -> None:
        transport = CatalogueTransport(90, default=30, maximum=30)

        list(_client(transport).signals.list_iter(limit_per_page=50))

        assert [r.params["offset"] for r in transport.requests] == [0, 30, 60]

    def test_the_last_page_ends_iteration_without_a_further_request(self) -> None:
        transport = CatalogueTransport(60, default=30, maximum=30)

        list(_client(transport).signals.list_iter(limit_per_page=30))

        assert len(transport.requests) == 2

    def test_an_empty_catalogue_yields_nothing_and_asks_once(self) -> None:
        transport = CatalogueTransport(0, default=30, maximum=30)

        assert list(_client(transport).signals.list_iter()) == []
        assert len(transport.requests) == 1


class TestIterationRefusesToLoop:
    def test_an_invalid_page_is_rejected_before_any_item_is_yielded(self) -> None:
        transport = StuckTransport(rows=10, next_offset=0)
        iterator = _client(transport).signals.list_iter()

        with pytest.raises(MalformedResponseError):
            next(iterator)

    def test_an_empty_page_cannot_continue_to_another_billable_request(self) -> None:
        transport = StuckTransport(rows=0, next_offset=30)

        with pytest.raises(MalformedResponseError):
            list(_client(transport).signals.list_iter())
        assert len(transport.requests) == 1

    def test_a_response_for_another_offset_is_rejected_before_yield(self) -> None:
        def fetch(offset: int, limit: int) -> PaginatedResponse[Record]:
            return _page(items=[Record(name="a")], total=1, offset=offset + 1,
                         limit=limit, has_more=False)

        with pytest.raises(MalformedResponseError):
            next(paginate_iter(fetch))

    def test_a_page_pointing_at_itself_raises(self) -> None:
        transport = StuckTransport(rows=10, next_offset=0)

        with pytest.raises(MalformedResponseError):
            list(_client(transport).signals.list_iter())

    def test_a_page_pointing_backwards_raises(self) -> None:
        transport = StuckTransport(rows=10, next_offset=-5)

        with pytest.raises(MalformedResponseError):
            list(_client(transport).signals.list_iter())

    def test_an_empty_page_claiming_more_raises(self) -> None:
        transport = StuckTransport(rows=0, next_offset=0)

        with pytest.raises(MalformedResponseError):
            list(_client(transport).signals.list_iter())

    def test_the_request_is_not_repeated_before_raising(self) -> None:
        transport = StuckTransport(rows=10, next_offset=0)

        with pytest.raises(MalformedResponseError):
            list(_client(transport).signals.list_iter())

        assert len(transport.requests) == 1

    def test_a_page_with_nothing_to_advance_past_raises(self) -> None:
        # An endpoint that does not report `next_offset` has one derived from the rows
        # it returned. No rows means no progress, which must stop rather than repeat.
        def fetch_page(offset: int, limit: int) -> PaginatedResponse[Record]:
            return _page(
                items=[], total=500, offset=offset, limit=limit, has_more=True
            )

        with pytest.raises(MalformedResponseError):
            list(paginate_iter(fetch_page))


class TestPagingFieldsWhenTheServerReportsThem:
    def test_reported_values_are_kept(self) -> None:
        page = _page(
            items=[Record(name="a")],
            total=96,
            offset=0,
            limit=50,
            has_more=True,
            next_offset=30,
        )

        assert page.has_more is True
        assert page.next_offset == 30

    def test_a_reported_last_page_is_not_overridden(self) -> None:
        page = _page(
            items=[Record(name="a")],
            total=96,
            offset=0,
            limit=50,
            has_more=False,
            next_offset=None,
        )

        assert page.has_more is False
        assert page.next_offset is None


class TestPagingFieldsWhenTheServerOmitsThem:
    def test_strategy_iteration_preserves_filters_and_numeric_string_metadata(self) -> None:
        class StrategyTransport(_RecordingTransport):
            def _body(self, params: dict[str, Any]) -> dict[str, Any]:
                offset = params["skip"]
                return {
                    "strategies": [
                        {"id": str(i), "name": f"Strategy {i}", "asset": "BTC",
                         "status": "inactive", "created_at": "2026-01-01T00:00:00Z"}
                        for i in range(offset, min(offset + 2, 5))
                    ],
                    "total": "5", "skip": str(offset), "limit": "100",
                }

        transport = StrategyTransport()
        with _client(transport) as client:
            records = list(client.strategies.list_iter(include_archived=True))

        assert [record.id for record in records] == [str(i) for i in range(5)]
        assert [request.params["skip"] for request in transport.requests] == [0, 2, 4]
        assert all(request.params["include_archived"] is True for request in transport.requests)

    def test_paging_is_derived_after_numeric_string_coercion(self) -> None:
        page = _page(items=[Record(name="a")], total="2", offset="0", limit="50")

        assert page.total == 2
        assert page.offset == 0
        assert page.has_more is True
        assert page.next_offset == 1

    def test_iteration_covers_short_pages_without_server_paging_metadata(self) -> None:
        records = [Record(name=str(i)) for i in range(101)]
        offsets = []

        def fetch(offset: int, limit: int) -> PaginatedResponse[Record]:
            offsets.append(offset)
            return _page(items=records[offset:offset + 30], total=len(records), offset=offset, limit=limit)

        assert list(paginate_iter(fetch, limit_per_page=100)) == records
        assert offsets == [0, 30, 60, 90]

    def test_paging_metadata_survives_json_round_trip(self) -> None:
        page = _page(items=[Record(name="a")], total=96, offset=0, limit=50,
                     has_more=True, next_offset=30)

        restored = PaginatedResponse[Record].model_validate_json(page.model_dump_json())

        assert restored == page
        assert restored.next_offset == 30

    def test_more_results_are_derived_from_the_rows_returned(self) -> None:
        page = _page(items=[Record(name="a")], total=96, offset=0, limit=50)

        assert page.has_more is True
        assert page.next_offset == 1

    def test_the_final_page_reports_no_continuation(self) -> None:
        page = _page(
            items=[Record(name="a"), Record(name="b")], total=2, offset=0, limit=50
        )

        assert page.has_more is False
        assert page.next_offset is None

    def test_a_single_page_catalogue_terminates(self) -> None:
        page = _page(items=[Record(name="a")], total=1, offset=0, limit=50)

        assert page.has_more is False

    def test_an_empty_page_past_the_end_reports_no_continuation(self) -> None:
        page = _page(items=[], total=96, offset=96, limit=50)

        assert page.has_more is False
        assert page.next_offset is None
