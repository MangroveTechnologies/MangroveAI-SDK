from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field, StrictInt, StrictStr, field_validator, model_validator

from ._base import MangroveModel

_EXTERNAL_DECIMAL_RE = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
_EXTERNAL_MAX_DECIMAL_LENGTH = 128
_EXTERNAL_MAX_DECIMAL_DIGITS = 96


def _utc_timestamp(value: str | None, field: str) -> str | None:
    """Validate a UTC ISO timestamp without changing its wire spelling."""
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be an ISO-8601 UTC timestamp or null")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 UTC timestamp or null") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError(f"{field} must include a UTC offset")
    return value


def _exact_decimal(value: str, field: str, *, positive: bool = False, nonnegative: bool = False) -> str:
    """Require a finite, bounded exact-decimal string, matching the hosted contract."""
    if not isinstance(value, str) or not value or len(value) > _EXTERNAL_MAX_DECIMAL_LENGTH:
        raise ValueError(f"{field} must be an exact decimal string")
    if not _EXTERNAL_DECIMAL_RE.fullmatch(value):
        raise ValueError(f"{field} must be an exact decimal string")
    unsigned = value[1:] if value.startswith("-") else value
    whole, _, fraction = unsigned.partition(".")
    if len(whole) + len(fraction) > _EXTERNAL_MAX_DECIMAL_DIGITS:
        raise ValueError(f"{field} exceeds {_EXTERNAL_MAX_DECIMAL_DIGITS} decimal digits")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{field} must be an exact decimal string") from exc
    if positive and number <= 0:
        raise ValueError(f"{field} must be > 0")
    if nonnegative and number < 0:
        raise ValueError(f"{field} must be >= 0")
    return value


class ExternalExecutionOpenedEvent(MangroveModel):
    """First confirmed fill for one externally held position."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["opened"]
    sequence: Annotated[StrictInt, Field(gt=0)]
    event_id: StrictStr
    position_id: StrictStr
    asset: StrictStr
    filled_quantity: StrictStr
    occurred_at: StrictStr | None = None

    @field_validator("event_id", "position_id", "asset")
    @classmethod
    def _require_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be a non-empty string")
        return value

    @field_validator("filled_quantity")
    @classmethod
    def _validate_filled_quantity(cls, value: str) -> str:
        return _exact_decimal(value, "filled_quantity", positive=True)

    @field_validator("occurred_at")
    @classmethod
    def _validate_occurred_at(cls, value: str | None) -> str | None:
        return _utc_timestamp(value, "occurred_at")


class ExternalExecutionClosedEvent(MangroveModel):
    """Actual outcome for a position that is now fully flat."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["closed"]
    sequence: Annotated[StrictInt, Field(gt=0)]
    event_id: StrictStr
    position_id: StrictStr
    asset: StrictStr
    realized_pnl: StrictStr
    fees: StrictStr
    occurred_at: StrictStr | None = None

    @field_validator("event_id", "position_id", "asset")
    @classmethod
    def _require_nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be a non-empty string")
        return value

    @field_validator("realized_pnl")
    @classmethod
    def _validate_realized_pnl(cls, value: str) -> str:
        return _exact_decimal(value, "realized_pnl")

    @field_validator("fees")
    @classmethod
    def _validate_fees(cls, value: str) -> str:
        return _exact_decimal(value, "fees", nonnegative=True)

    @field_validator("occurred_at")
    @classmethod
    def _validate_occurred_at(cls, value: str | None) -> str | None:
        return _utc_timestamp(value, "occurred_at")


ExternalExecutionEvent = Annotated[
    ExternalExecutionOpenedEvent | ExternalExecutionClosedEvent,
    Field(discriminator="kind"),
]


class ExternalExecutionRequest(MangroveModel):
    """Opt-in v2 event batch for a stateless hosted evaluation."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal[2] = 2
    observed_at: StrictStr
    events: list[ExternalExecutionEvent] = Field(max_length=512)

    @field_validator("contract_version", mode="before")
    @classmethod
    def _require_exact_contract_version_type(cls, value: Any) -> Any:
        if type(value) is not int or value != 2:
            raise ValueError("contract_version must be the integer 2")
        return value

    @field_validator("observed_at")
    @classmethod
    def _validate_observed_at(cls, value: str) -> str:
        return _utc_timestamp(value, "observed_at") or value

    @model_validator(mode="after")
    def _validate_event_order_and_times(self) -> ExternalExecutionRequest:
        for previous, current in zip(self.events, self.events[1:]):
            if previous.sequence >= current.sequence:
                raise ValueError("events must have strictly increasing sequence numbers")
        observed = datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))
        for event in self.events:
            if event.occurred_at is not None:
                occurred = datetime.fromisoformat(event.occurred_at.replace("Z", "+00:00"))
                if occurred > observed:
                    raise ValueError("occurred_at cannot be after observed_at")
        return self


class ExternalExecutionReceipt(MangroveModel):
    """Typed view of a retained event receipt; unknown future fields survive."""

    sequence: Annotated[StrictInt, Field(gt=0)]
    event_id: StrictStr
    position_id: StrictStr
    kind: Literal["opened", "closed"]
    sha256: StrictStr
    occurred_at: StrictStr | None = None
    accounting_at: StrictStr

    @field_validator("occurred_at", "accounting_at")
    @classmethod
    def _validate_receipt_timestamp(cls, value: str | None, info) -> str | None:
        return _utc_timestamp(value, info.field_name)


class ExternalExecutionAck(MangroveModel):
    """Typed acknowledgment state returned under ``execution_state``."""

    contract_version: Literal[2]
    applied_through: Annotated[StrictInt, Field(ge=0)]
    receipts: list[ExternalExecutionReceipt] = Field(default_factory=list)
    active_position_ids: list[StrictStr] = Field(default_factory=list)
    last_observed_at: StrictStr | None = None

    @field_validator("last_observed_at")
    @classmethod
    def _validate_last_observed_at(cls, value: str | None) -> str | None:
        return _utc_timestamp(value, "last_observed_at")


class CreateAccountRequest(MangroveModel):
    """Request body for creating a trading account."""

    account_type: str
    name: str | None = None
    initial_balance: float | None = None
    min_balance_threshold: float | None = None
    min_trade_amount: float | None = None
    max_open_positions: int | None = None
    max_trades_per_day: int | None = None
    max_risk_per_trade: float | None = None
    risk_params: dict[str, Any] | None = None


class Account(MangroveModel):
    """A trading account (paper or live)."""

    id: str
    org_id: str
    user_id: str
    account_type: str
    name: str | None = None
    cash_balance: float
    account_value: float
    min_balance_threshold: float | None = None
    min_trade_amount: float | None = None
    max_open_positions: int | None = None
    max_trades_per_day: int | None = None
    max_risk_per_trade: float | None = None
    risk_params: dict[str, Any] | None = None
    active: bool = True
    created_at: str | None = None
    updated_at: str | None = None


class Position(MangroveModel):
    """A trading position."""

    id: str
    org_id: str | None = None
    user_id: str | None = None
    account_id: str
    strategy_id: str | None = None
    asset: str
    exchange: str | None = None
    entry_price: float
    exit_price: float | None = None
    position_size: float
    cost: float | None = None
    value_at_close: float | None = None
    open: bool
    exit_reason: str | None = None
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    created_at: str | None = None
    entry_timestamp: str | None = None
    exit_timestamp: str | None = None


class Trade(MangroveModel):
    """A completed trade record."""

    id: str
    org_id: str | None = None
    user_id: str | None = None
    account_id: str | None = None
    position_id: str | None = None
    outcome: str
    profit_loss: float
    profit_loss_pct: float | None = None
    asset: str
    exchange: str | None = None
    strategy_name: str | None = None
    entry_price: float
    exit_price: float
    position_size: float
    beginning_balance: float | None = None
    ending_balance: float | None = None
    closed_at: str | None = None


class EvaluateResult(MangroveModel):
    """Result of evaluating a strategy against current market data."""

    success: bool
    strategy_id: str | None = None
    strategy_name: str | None = None
    asset: str | None = None
    current_price: float | None = None
    timestamp: str | None = None
    execution_state: dict[str, Any] | None = None
    new_orders: list[dict[str, Any]] | None = None
    # Stateless lane only: present when the request carried caller-owned
    # open_positions. The UPDATED set (surviving + newly entered, resting
    # bracket orders included) -- persist it and echo it back on the next
    # evaluation, exactly like execution_state.
    open_positions: list[dict[str, Any]] | None = None
    # External v2 only: speculative hosted position payloads for newly
    # modeled entries. These are distinct from broker-confirmed open_positions.
    position_templates: list[dict[str, Any]] | None = None
    external_execution_disposition: Literal["evaluated", "duplicate_bar"] | None = None
    execution_time_seconds: float | None = None
    error: str | None = None

    @property
    def external_execution_ack(self) -> ExternalExecutionAck | None:
        """Typed v2 acknowledgment, while ``execution_state`` stays raw and forward-compatible."""
        if self.execution_state is None:
            return None
        raw = self.execution_state.get("external_execution")
        if not isinstance(raw, dict) or raw.get("contract_version") != 2:
            return None
        return ExternalExecutionAck.model_validate(raw)


class BulkEvaluateResult(MangroveModel):
    """Envelope for bulk strategy evaluation.

    ``results`` carries one ``EvaluateResult``-shaped entry per input
    strategy (in the same order as the request). Per-strategy failures
    are captured in each entry's ``error`` field without aborting the
    batch — check ``results[i].success`` per row.

    ``data_fetches`` is the number of unique ``(asset, timeframe)``
    market-data API calls the server actually made. Bulk evaluation
    shares fetches across strategies that need the same OHLCV slice,
    so this number is typically ≪ ``len(results)``.

    ``error`` is set only when the batch itself failed to start
    (e.g. malformed top-level body); in that case ``success=False``
    and ``results=[]``.
    """

    success: bool
    results: list[EvaluateResult] = []
    data_fetches: int = 0
    total_execution_time_seconds: float = 0.0
    error: str | None = None


# ---------------------------------------------------------------------------
# Portfolio (batch dashboard read)
# ---------------------------------------------------------------------------


class PortfolioRecentTrade(MangroveModel):
    """One trade entry inside `PortfolioEntry.recent_trades` — last 5
    trades for a given strategy.
    """

    id: str | None = None
    asset: str | None = None
    outcome: str | None = None
    profit_loss: float | None = None
    profit_loss_pct: float | None = None
    closed_at: str | None = None


class PortfolioEntry(MangroveModel):
    """Dashboard-ready snapshot for one strategy.

    Pulled by `get_portfolio(strategy_ids)`. Designed for UI cards that
    need a strategy's name + asset + status + most-recent execution
    state + last 5 trades in one batched read instead of an N+1 RTT
    fan-out.

    Field names mirror the server response shape verbatim — most
    notably ``strategy_name`` (not ``name``) and ``open_positions_count``
    (not ``open_positions``). ``status`` is only populated when the
    server has it available (e.g. for non-archived strategies).
    """

    strategy_id: str
    strategy_name: str | None = None
    asset: str | None = None
    status: str | None = None
    execution_state: dict[str, Any] | None = None
    last_evaluated_at: str | None = None
    open_positions_count: int | None = None
    recent_trades: list[PortfolioRecentTrade] = []


class PortfolioResponse(MangroveModel):
    """Envelope returned by `GET /execution/portfolio`.

    ``results`` is the list of strategies the server found (in request
    order, with missing ones omitted). ``missing`` lists IDs that did
    not match any strategy the caller has access to — useful for
    distinguishing "deleted" from "no permission".
    """

    results: list[PortfolioEntry] = []
    missing: list[str] = []
