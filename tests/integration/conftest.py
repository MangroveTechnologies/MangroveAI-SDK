"""Every live test skips, rather than fails, when the API key's metered allowance is used up."""
from __future__ import annotations

from collections.abc import Generator

import pytest

from tests.integration.quota import skip_on_exhausted_quota


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Generator[None, object, object]:
    with skip_on_exhausted_quota():
        return (yield)
