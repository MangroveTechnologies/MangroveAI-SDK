"""Models for the MangroveOracle endpoints reached via MangroveAI's reverse proxy.

The Oracle surface is exposed under MangroveAI at ``/api/v1/oracle/*``. This
module mirrors the Pydantic shapes Oracle itself ships (see
``MangroveOracle/src/models/sieve.py`` and ``data_query.py``) so the SDK can
validate request/response shapes without round-tripping through dynamic dicts.
"""
from __future__ import annotations

from typing import Any

from ._base import MangroveModel

# ---------------------------------------------------------------------------
# SIEVE classifier scoring
# ---------------------------------------------------------------------------

class SignalSpec(MangroveModel):
    """One entry or exit signal inside a `StrategyInput`."""

    name: str
    signal_type: str  # "TRIGGER" | "FILTER"
    timeframe: str | None = None
    params: dict[str, Any] = {}


class StrategyInput(MangroveModel):
    """MangroveAI-shaped strategy passed to SIEVE."""

    asset: str
    entry: list[SignalSpec]
    exit: list[SignalSpec]
    execution_config: dict[str, Any] | None = None


class RunInput(MangroveModel):
    """Raw run shape consumed by SIEVE — use when scoring rows already
    extracted from the Mangrove sweep corpus.
    """

    entry_json: str
    exit_json: str
    asset: str
    exec_config: dict[str, Any]


class SieveScoreRequest(MangroveModel):
    """Exactly one of `strategies` / `runs` must be set; ≤99 items per request."""

    strategies: list[StrategyInput] | None = None
    runs: list[RunInput] | None = None


class SievePrediction(MangroveModel):
    """Probabilities for one SIEVE-scored item.

    ``binary`` keys: ``p_no_trades`` + ``p_trades``.
    ``four_class`` keys: ``losing`` / ``no_trades`` / ``wash`` / ``winning``.
    Each dict sums to 1.0 within float32 tolerance.
    """

    binary: dict[str, float]
    four_class: dict[str, float]


class SieveScoreResponse(MangroveModel):
    """SIEVE score response with full provenance.

    ``model_version`` is a content hash of the bundled `.pt` + vocab files
    (format ``mangrove-sieve:<hash>``); changes when SIEVE is retrained.
    ``code_version`` is the Oracle dependency stack
    (``oracle:<ref> ai:<ref> kb:<ref> roots:<ref>``).
    """

    predictions: list[SievePrediction]
    count: int
    model_version: str
    code_version: str


# ---------------------------------------------------------------------------
# Data query
# ---------------------------------------------------------------------------

class DataQueryFilter(MangroveModel):
    """One filter clause on a data-query request."""

    col: str
    op: str  # "=", "!=", ">", ">=", "<", "<=", "in", "not in", "between"
    value: Any


class OrderBy(MangroveModel):
    """One ORDER BY clause for a data query.

    Mirrors MangroveOracle `models/data_query.OrderBy` — the server expects
    objects `{col, dir}`, NOT bare strings. `dir` is "asc" | "desc".
    """

    col: str
    dir: str = "desc"


class DataQueryRequest(MangroveModel):
    """Query the corpus of Oracle backtest results / OHLCV bars.

    The proxy whitelists the columns and filter operators server-side; the
    request only ever sees the curated surface.
    """

    table: str  # "results" | "ohlcv"
    select: list[str]
    filters: list[DataQueryFilter] = []
    order_by: list[OrderBy] | None = None
    limit: int = 100
    offset: int = 0


class DataQueryResponse(MangroveModel):
    """Rows + metadata for a data-query response (POST /oracle/data/query).

    Fields mirror MangroveOracle `models/data_query.QueryResponse`. `table`
    is echoed by Oracle >= v0.15.7 (kept optional so the SDK also parses
    responses from older servers that omit it). `code_version` is not sent
    by the data-query route today; kept optional for forward-compat.
    """

    rows: list[dict[str, Any]]
    row_count: int
    table: str | None = None
    total_bytes_billed: int | None = None
    cost_estimate_usd: float | None = None
    next_page_token: str | None = None
    code_version: str | None = None


# ---------------------------------------------------------------------------
# Oracle backtests (sync / async / bulk)
# ---------------------------------------------------------------------------

class OracleBacktestRequest(MangroveModel):
    """Backtest a single strategy against Oracle's engine.

    Shape mirrors `MangroveOracle/src/api/routes/backtest.py:123-275`. Most
    risk-management fields can be omitted; the server fills from canonical
    `trading_defaults.json`.
    """

    asset: str
    interval: str
    strategy_json: str
    # Optional risk-mgmt / execution fields — server-default-fillable
    initial_balance: float | None = None
    min_balance_threshold: float | None = None
    min_trade_amount: float | None = None
    max_open_positions: int | None = None
    max_trades_per_day: int | None = None
    max_risk_per_trade: float | None = None
    max_units_per_trade: float | None = None
    max_trade_amount: float | None = None
    volatility_window: int | None = None
    target_volatility: float | None = None
    volatility_mode: str | None = None
    enable_volatility_adjustment: bool | None = None
    cooldown_bars: int | None = None
    daily_momentum_limit: float | None = None
    weekly_momentum_limit: float | None = None
    # Date-range mode (one of: start+end, start only, lookback_months, none)
    start_date: str | None = None
    end_date: str | None = None
    lookback_months: int | None = None
    exchange: str | None = None
    max_hold_time_hours: int | None = None
    slippage_pct: float | None = None
    fee_pct: float | None = None
    execution_config: dict[str, Any] | None = None
    # "full" (default) or "quick"
    mode: str | None = None


class OracleBulkBacktestRequest(MangroveModel):
    """Evaluate many strategies over a shared date range; one OHLCV fetch
    per unique (asset, timeframe).
    """

    start_date: str
    end_date: str
    initial_balance: float
    min_balance_threshold: float
    min_trade_amount: float
    max_open_positions: int
    max_trades_per_day: int
    max_risk_per_trade: float
    max_units_per_trade: float
    max_trade_amount: float
    volatility_window: int
    target_volatility: float
    volatility_mode: str
    enable_volatility_adjustment: bool
    cooldown_bars: int
    daily_momentum_limit: float
    weekly_momentum_limit: float
    strategy_ids: list[str] | None = None
    strategy_configs: list[dict[str, Any]] | None = None
    execution_config: dict[str, Any] | None = None
    max_hold_time_hours: int | None = None
    slippage_pct: float | None = None
    fee_pct: float | None = None
    mode: str | None = None


class OracleBacktestResult(MangroveModel):
    """Result of a single Oracle backtest."""

    success: bool
    metrics: dict[str, Any]
    execution_time_seconds: float | None = None
    trade_count: int | None = None
    strategy_names: list[str] | None = None
    trade_history: list[dict[str, Any]] | None = None
    denied_signals: list[dict[str, Any]] | None = None
    error: str | None = None


class OracleAsyncBacktestSubmission(MangroveModel):
    """202 Accepted shape for async backtest submission."""

    backtest_id: str
    status: str


class OracleAsyncBacktestStatus(MangroveModel):
    """Polling response for an async backtest."""

    backtest_id: str
    status: str
    metrics: dict[str, Any] | None = None
    trade_history: list[dict[str, Any]] | None = None
    execution_time_seconds: float | None = None
    trade_count: int | None = None
    strategy_names: list[str] | None = None
    error_message: str | None = None


class OracleBulkBacktestResult(MangroveModel):
    """Bulk backtest result envelope."""

    success: bool
    results: list[dict[str, Any]]
    data_fetches: int
    total_execution_time_seconds: float
    error: str | None = None


# ---------------------------------------------------------------------------
# Experiments (sweep lifecycle)
# ---------------------------------------------------------------------------


class ExperimentSummary(MangroveModel):
    """Compact experiment view returned by `list_experiments`.

    Lifecycle status values:
      - ``draft``     — created but not yet validated; editable.
      - ``validated`` — validation passed; ready to launch.
      - ``launched``  — fan-out in progress (``completed < total_runs``).
      - ``completed`` — all child backtests finished.
      - ``paused``    — fan-out paused by the operator.
      - ``failed``    — terminal failure during launch.
    """

    experiment_id: str
    name: str | None = None
    status: str
    total_runs: int | None = None
    completed: int | None = None
    search_mode: str | None = None  # "grid" | "random"
    created_at: str | None = None


class ExperimentCreated(MangroveModel):
    """Response shape from `POST /experiments` (201)."""

    experiment_id: str
    status: str  # always "draft" on first create
    created_at: str | None = None
    org_id: str | None = None


class ExperimentStatus(MangroveModel):
    """Response shape for launch / pause / update transitions.

    `experiment_id` is optional because not every transition echoes it:
    `launch` and `update` return ``{experiment_id, status}``, but `pause`
    returns ``{status: "paused"}`` alone. (Validate has its own shape —
    see `ExperimentValidation`.)
    """

    experiment_id: str | None = None
    status: str


class ExperimentValidation(MangroveModel):
    """Response shape from `POST /experiments/{id}/validate` (HTTP 200).

    Validation does NOT return the {experiment_id, status} transition
    shape — it returns the config-check result. On a config that can't be
    validated Oracle still returns 200 with ``valid: false`` and the
    reasons in ``errors``; hard failures (e.g. tier caps) come back as
    4xx with the detail in the error body instead.
    """

    valid: bool
    total_runs: int
    errors: list[str] = []
    warnings: list[str] = []


class ExperimentDeleted(MangroveModel):
    """Response shape from `DELETE /experiments/{id}`."""

    status: str  # "deleted"


# ---------------------------------------------------------------------------
# Results (Oracle backtest results — paginated)
# ---------------------------------------------------------------------------


class OracleResultsPage(MangroveModel):
    """One page of backtest results for an experiment.

    Each entry in ``results`` is the wide-format Oracle backtest result
    row — metrics + trade history + provenance. The schema stays loose
    (``dict[str, Any]``) because Oracle adds columns each release;
    locking it down forces SDK bumps for cosmetic field additions.
    """

    total: int
    offset: int
    limit: int
    results: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Simulate (single-strategy runs without persisting)
# ---------------------------------------------------------------------------


class SimulateRunResponse(MangroveModel):
    """Response from POST /oracle/simulate/run — one strategy applied to a
    dataset without persisting (interactive "try this rule and see").

    Shape verified against MangroveOracle `src/services/simulator.py` (the
    route returns this dict directly): the dataset it ran on, the
    reconstructed strategy config, and the visualization payload (trades,
    ohlcv, metrics) plus an optional error. (Earlier this model guessed
    `simulation_id`/`status`/`result`, which the server never returns — the
    real data was silently dropped into pydantic extras.)
    """

    dataset_file: str | None = None
    strategy_config: dict[str, Any] | None = None
    trades: list[dict[str, Any]] = []
    ohlcv: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    error: str | None = None


# ---------------------------------------------------------------------------
# Leaderboard (curated personas — display wrappers for the deployed strategies)
# ---------------------------------------------------------------------------


class LeaderboardPersona(MangroveModel):
    """One curated persona on the public leaderboard.

    Personas wrap deployed strategies for the public-facing dashboard
    (e.g. mangrovedeveloper.ai/leaderboard). The actual live execution
    state lives under ``/oracle/deployed/*`` — use
    ``list_deployed_strategies()`` etc. to read it.
    """

    id: str
    name: str
    avatar: str | None = None
    deployed_strategy_ids: list[str] = []
    rank: int | None = None


class LeaderboardResponse(MangroveModel):
    """Top-level shape returned by GET /oracle/leaderboard."""

    personas: list[LeaderboardPersona] = []


# ---------------------------------------------------------------------------
# Deployed strategies (live execution state of curated deployed strategies)
# ---------------------------------------------------------------------------


class DeployedStrategy(MangroveModel):
    """A single curated strategy currently running in paper-trading mode.

    Field names mirror what Oracle's /deployed/strategies endpoint
    actually returns (verified against api.mangrovedeveloper.ai on
    2026-05-31). ``persona_id`` is not on the strategy row itself —
    look up the owning persona via ``LeaderboardPersona.deployed_strategy_ids``.
    """

    strategy_id: str
    name: str
    asset: str | None = None
    timeframe: str | None = None
    experiment_id: str | None = None
    run_index: int | None = None
    trigger_name: str | None = None
    num_open_positions: int | None = None
    total_trades: int | None = None
    last_price: float | None = None
    last_tick_at: str | None = None
    last_tick_status: str | None = None
    health: str | None = None
    # Free-form sub-payloads. Keep loose to avoid breaking on every
    # backtest-metric / position-shape iteration server-side.
    equity: list[Any] | None = None
    positions: list[Any] | None = None
    trades: list[Any] | None = None
    backtest_metrics: dict[str, Any] | None = None
