from __future__ import annotations

import pytest

from mangrove_ai import MangroveAI
from mangrove_ai._transport._mock import MockTransport


@pytest.fixture
def mock_transport() -> MockTransport:
    """A bare MockTransport for low-level testing."""
    return MockTransport()


@pytest.fixture
def client(mock_transport: MockTransport) -> MangroveAI:
    """A MangroveAI client wired to a MockTransport.

    Access the mock via client._http to add responses:
        client._http.add_response("GET", "/strategies/", json={...})
    """
    return MangroveAI(api_key="test_abc123", environment="local", httpx_client=mock_transport)
