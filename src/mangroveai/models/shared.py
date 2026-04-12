from __future__ import annotations

from ._base import MangroveModel


class SuccessResponse(MangroveModel):
    """Generic success response."""

    success: bool
    message: str | None = None
