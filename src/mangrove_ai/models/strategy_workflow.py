"""Wire models for the server-owned strategy workflow."""
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SaveStrategyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy_name: str
    asset: str
    entry_signals: list[dict[str, Any]] | None = None
    exit_signals: list[dict[str, Any]] | None = None
    regime_direction: str | None = None
    constraints: dict[str, Any] | None = None
    regime_override: bool = False
    source_experiment_id: str | None = None
    source_run_index: int | None = None
    quote_token: str | None = None
    market_data_venue: str | None = None


class SavedStrategy(BaseModel):
    model_config = ConfigDict(extra="allow")
    strategy_id: str
    created: bool
    name: str
    asset: str
    status: str
    interval: str | None = None
    rules: dict[str, Any]
    resolved_config: dict[str, Any]
    base_token: str
    quote_token: str
    market_data_venue: str


class SkillDocument(BaseModel):
    model_config = ConfigDict(extra="allow")
    skill: str
    version: str
    instructions: str
    required_tools: list[str]
    resources: list[str] = Field(default_factory=list)
    section: str | None = None
    resource: str | None = None
