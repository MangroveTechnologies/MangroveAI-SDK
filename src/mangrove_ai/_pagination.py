from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Generic, TypeVar

from pydantic import BaseModel, model_validator

from .exceptions import MalformedResponseError

T = TypeVar("T", bound=BaseModel)


class PaginatedResponse(BaseModel, Generic[T]):
    """A single page of results from a paginated endpoint.

    ``has_more`` and ``next_offset`` carry the server's own answer on endpoints that
    report them, and are otherwise derived from the page itself, so both fields mean
    the same thing to a caller whichever endpoint produced the page.

    ``total`` is the number of records matching the request, not the number returned
    on this page.
    """

    items: list[T]
    total: int
    offset: int
    limit: int
    has_more: bool = False
    next_offset: int | None = None

    @model_validator(mode="after")
    def _fill_unreported_paging(self) -> PaginatedResponse[T]:
        # Derived from the rows actually returned, never from `limit`. A server may
        # serve a smaller page than the one requested, and measuring progress by the
        # requested size would step over the rows in between.
        page_end = self.offset + len(self.items)
        if "has_more" not in self.model_fields_set:
            self.has_more = page_end < self.total
        if self.has_more and self.next_offset is None:
            self.next_offset = page_end
        return self


def paginate_iter(
    fetch_page: Callable[[int, int], PaginatedResponse[T]],
    limit_per_page: int = 100,
) -> Iterator[T]:
    """Yields items one at a time, fetching pages as needed.

    ``limit_per_page`` is the page size requested. The server decides the size it
    actually serves, so it is never used to work out where the next page starts.

    Raises:
        MalformedResponseError: A page reported further results without a usable
            offset to continue from. Continuing would re-request the same page
            indefinitely, and every request is billable.
    """
    offset = 0
    while True:
        page = fetch_page(offset, limit_per_page)
        if page.offset != offset:
            raise MalformedResponseError("Page response does not match the requested offset.")
        if page.has_more and (
            not page.items or page.next_offset is None or page.next_offset <= offset
        ):
            raise MalformedResponseError(
                f"Page at offset {offset} reports further results but does not "
                "advance past it."
            )
        yield from page.items

        if not page.has_more:
            return
        assert page.next_offset is not None
        offset = page.next_offset
