from __future__ import annotations

from typing import Any

from ._base import MangroveModel


class StrategyListItem(MangroveModel):
    """Strategy summary as returned in list views."""

    id: str
    name: str
    asset: str
    status: str
    created_at: str
    strategy_type: str | None = None
    description: str | None = None
    # Archive view-state (reversible; strategies are never hard-deleted).
    archived: bool = False
    archived_at: str | None = None


class StrategyDetail(MangroveModel):
    """Full strategy detail including rules and execution state."""

    id: str
    name: str
    user_id: str
    org_id: str
    asset: str
    rules: dict[str, Any]
    status: str
    created_at: str
    execution_config: dict[str, Any] | None = None
    execution_state: dict[str, Any] | None = None
    session_id: str | None = None
    parent_strategy_id: str | None = None
    content_hash: str | None = None
    strategy_type: str | None = None
    description: str | None = None
    # Archive view-state (reversible; strategies are never hard-deleted).
    archived: bool = False
    archived_at: str | None = None


class StrategyArchiveResult(MangroveModel):
    """Response from archiving or unarchiving a strategy.

    Strategies are never deleted; archiving hides a strategy from the default
    list views and stops it counting toward the per-tier strategy limit (and is
    reversible via unarchive).
    """

    success: bool
    strategy_id: str
    archived: bool


class CreateStrategyRequest(MangroveModel):
    """Request body for creating a new strategy."""

    name: str
    asset: str
    entry: list[dict[str, Any]]
    exit: list[dict[str, Any]] | None = None
    reward_factor: float | None = None
    status: str = "inactive"
    execution_config: dict[str, Any] | None = None
    session_id: str | None = None
    strategy_type: str | None = None
    description: str | None = None


class UpdateStrategyRequest(MangroveModel):
    """Request body for updating a strategy."""

    name: str | None = None
    asset: str | None = None
    rules: dict[str, Any] | None = None
    execution_config: dict[str, Any] | None = None
