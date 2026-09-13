"""Models for the execution-config schema (``client.config.get_execution_config_schema``).

Field names match the MangroveAI copilot's ``get_execution_config_schema`` tool.
"""
from __future__ import annotations

from typing import Any

from ._base import MangroveModel


class ExecutionConfigParam(MangroveModel):
    """What one execution_config parameter is, does, and may be set to."""

    status: str | None = None
    """``tunable`` (strategy character), ``guardrail`` (account/size bound), ``gated``
    (only takes effect when ``gate_field`` is truthy), ``unused`` (no runtime effect)
    or ``superseded``."""
    description: str | None = None
    effect: str | None = None
    """The effect of raising or lowering it."""
    type: str | None = None
    """``"int"`` or ``"float"`` when numeric."""
    min: float | None = None
    max: float | None = None
    min_exclusive: bool | None = None
    max_exclusive: bool | None = None
    gate_field: str | None = None
    gate_required: Any | None = None
    choices: list[Any] | None = None


class TransactionCosts(MangroveModel):
    """Fee and slippage. Canon, not part of an execution config, not settable per strategy."""

    fee_pct: float | None = None
    slippage_pct: float | None = None
    source: str | None = None
    per_strategy: bool | None = None


class ExecutionConfigSchema(MangroveModel):
    """Every execution_config parameter: default, effect, bounds and status."""

    defaults: dict[str, Any]
    """The flattened canon execution config -- what a strategy gets for an omitted key."""
    param_glossary: dict[str, ExecutionConfigParam]
    transaction_costs: TransactionCosts
    percent_scale_note: str | None = None
