from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class PaginatedResponse(BaseModel, Generic[T]):
    """A single page of results from a paginated endpoint."""

    items: list[T]
    total: int
    offset: int
    limit: int

    @property
    def has_more(self) -> bool:
        return self.offset + self.limit < self.total


def paginate_iter(
    fetch_page: Callable[[int, int], PaginatedResponse[T]],
    limit_per_page: int = 100,
) -> Iterator[T]:
    """Yields items one at a time, fetching pages as needed."""
    offset = 0
    while True:
        page = fetch_page(offset, limit_per_page)
        yield from page.items
        if not page.has_more:
            break
        offset += limit_per_page
