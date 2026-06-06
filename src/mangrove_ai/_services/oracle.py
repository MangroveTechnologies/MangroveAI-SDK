"""MangroveOracle endpoints reached through MangroveAI's reverse proxy.

All methods POST to ``/oracle/<path>`` via the core (v1) transport. The
upstream Oracle service handles the actual SIEVE scoring, BigQuery query
serving, and backtest engine. This service is a thin typed wrapper.
"""
from __future__ import annotations

from typing import Any

from .._transport._service import ServiceTransport
from ..models.oracle import (
    DataQueryRequest,
    DataQueryResponse,
    DeployedStrategy,
    ExperimentCreated,
    ExperimentDeleted,
    ExperimentStatus,
    ExperimentSummary,
    ExperimentValidation,
    LeaderboardResponse,
    OracleAsyncBacktestStatus,
    OracleAsyncBacktestSubmission,
    OracleBacktestRequest,
    OracleBacktestResult,
    OracleBulkBacktestRequest,
    OracleBulkBacktestResult,
    OracleResultsPage,
    SieveScoreRequest,
    SieveScoreResponse,
    SimulateRunResponse,
)

SIEVE_MAX_ITEMS_PER_REQUEST = 99


class OracleService:
    """Score strategies through SIEVE, query the corpus, or run backtests."""

    def __init__(self, core_transport: ServiceTransport, v2_transport: ServiceTransport) -> None:
        self._core = core_transport
        # v2 transport currently unused but kept for parity with BacktestingService —
        # future Oracle endpoints (e.g. streaming SSE for sweep progress) may use it.
        self._v2 = v2_transport

    def _core_request(self, method: str, path: str, **kwargs: Any) -> dict:
        response = self._core.request(method, path, **kwargs)
        return response.json()

    # Convenience helpers that mirror BaseService — OracleService stays a
    # standalone class (not a BaseService subclass) because it juggles
    # two transports, but the new experiment / results / metadata
    # methods benefit from the same typed-validation shorthand.
    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        return self._core_request(method, path, **kwargs)

    def _request_model(
        self,
        method: str,
        path: str,
        model: type[Any],
        **kwargs: Any,
    ) -> Any:
        data = self._core_request(method, path, **kwargs)
        return model.model_validate(data)

    # ------------------------------------------------------------------ #
    # SIEVE
    # ------------------------------------------------------------------ #
    def sieve_score(self, request: SieveScoreRequest) -> SieveScoreResponse:
        """Score up to 99 strategies through the Mangrove SIEVE classifier.

        Returns binary go/no-go probabilities and 4-class outcome
        probabilities per item, plus ``model_version`` and ``code_version``
        for provenance.

        Args:
            request: ``SieveScoreRequest`` with exactly one of
                ``strategies`` (MangroveAI-shaped Strategy objects) or
                ``runs`` (raw run dicts) set. Maximum 99 items per request.

        Raises:
            ValueError: when more than 99 items are supplied or when both
                / neither input field is set (caught client-side before the
                request is sent, mirroring the server's HTTP 413 / 400).
        """
        payload = request.model_dump(exclude_none=True)
        has_strategies = bool(payload.get("strategies"))
        has_runs = bool(payload.get("runs"))
        if has_strategies == has_runs:
            raise ValueError(
                "Provide exactly one of `strategies` or `runs` (and not an empty list)"
            )
        item_count = len(payload.get("strategies") or payload.get("runs") or [])
        if item_count > SIEVE_MAX_ITEMS_PER_REQUEST:
            raise ValueError(
                f"Max {SIEVE_MAX_ITEMS_PER_REQUEST} items per request, got {item_count}"
            )

        data = self._core_request("POST", "/oracle/sieve/score", json=payload)
        return SieveScoreResponse.model_validate(data)

    # ------------------------------------------------------------------ #
    # Data query (BigQuery proxy)
    # ------------------------------------------------------------------ #
    def data_query(self, request: DataQueryRequest) -> DataQueryResponse:
        """Run a curated query against the Oracle corpus (results / ohlcv).

        Columns and filter operators are whitelisted server-side.
        """
        data = self._core_request(
            "POST", "/oracle/data/query", json=request.model_dump(exclude_none=True)
        )
        return DataQueryResponse.model_validate(data)

    # ------------------------------------------------------------------ #
    # Backtests
    # ------------------------------------------------------------------ #
    def backtest(self, request: OracleBacktestRequest) -> OracleBacktestResult:
        """Run a single-strategy backtest synchronously."""
        data = self._core_request(
            "POST", "/oracle/backtest", json=request.model_dump(exclude_none=True)
        )
        return OracleBacktestResult.model_validate(data)

    def backtest_async(
        self, request: OracleBacktestRequest
    ) -> OracleAsyncBacktestSubmission:
        """Submit a backtest for async execution; returns a backtest_id."""
        data = self._core_request(
            "POST", "/oracle/backtest/async", json=request.model_dump(exclude_none=True)
        )
        return OracleAsyncBacktestSubmission.model_validate(data)

    def backtest_poll(self, backtest_id: str) -> OracleAsyncBacktestStatus:
        """Poll the status / result of an async backtest by ID."""
        data = self._core_request("GET", f"/oracle/backtest/async/{backtest_id}/status")
        return OracleAsyncBacktestStatus.model_validate(data)

    def backtest_bulk(
        self, request: OracleBulkBacktestRequest
    ) -> OracleBulkBacktestResult:
        """Evaluate many strategies over a shared date range in one call."""
        data = self._core_request(
            "POST", "/oracle/backtest/bulk", json=request.model_dump(exclude_none=True)
        )
        return OracleBulkBacktestResult.model_validate(data)

    # ------------------------------------------------------------------ #
    # Experiments (sweep lifecycle)
    # ------------------------------------------------------------------ #
    #
    # Lifecycle:
    #   create -> [update]* -> validate -> launch -> (running) -> completed
    #                                                     |
    #                                                     +-> pause -> resume
    #                                                     +-> delete
    #
    # An experiment is an up-to-99-strategy parameter sweep: a strategy
    # template plus a grid (or random-search) over signal params, run
    # against one or more datasets. The lifecycle is intentionally
    # explicit — validate before launch, separate from create — so the
    # operator can check Oracle's read of the config (n_param_combos,
    # estimated cost) before paying for the fan-out.
    #
    # Costs: every POST against /experiments + /experiments/{id}/launch
    # counts as 1 unit against api_calls quota (1 unit per HTTP call,
    # not per child backtest). x402 callers pay $0.25 per call.

    def create_experiment(
        self,
        experiment_config: dict[str, Any],
    ) -> ExperimentCreated:
        """Create a new experiment in ``draft`` status.

        Args:
            experiment_config: Full experiment config dict. At minimum
                ``name``. See Oracle's ``ExperimentConfig`` Pydantic
                model for the full surface (datasets, search_mode,
                entry_signals, exit_signals, execution_config,
                random_signals, grid_signals, pairs, rotation_params).
                Typed as a dict to keep the SDK forward-compatible as
                Oracle adds fields.

        Returns:
            ``ExperimentCreated`` with the assigned ``experiment_id``
            (format ``exp_<timestamp>``) and ``status: "draft"``.
        """
        return self._request_model(
            "POST", "/oracle/experiments",
            ExperimentCreated,
            json=experiment_config,
        )

    def list_experiments(self) -> list[ExperimentSummary]:
        """List all experiments for the caller's org.

        Returns compact summary records (no full config). Note: this
        endpoint can be slow under load — the server-side proxy may
        return 504 if upstream Oracle is processing a large fan-out.
        Use ``get_experiment(id)`` for individual lookups in that case.
        """
        data = self._request("GET", "/oracle/experiments")
        return [ExperimentSummary.model_validate(e) for e in data]

    def get_experiment(self, experiment_id: str) -> dict[str, Any]:
        """Fetch full experiment config including current progress.

        Returns the experiment's full config (datasets, signals, grid
        params, execution_config, etc.) plus ``completed_runs`` for
        live progress tracking. Typed as ``dict[str, Any]`` to mirror
        Oracle's ``ExperimentConfig`` shape without forcing the SDK to
        track every config-schema change.
        """
        return self._request("GET", f"/oracle/experiments/{experiment_id}")

    def update_experiment(
        self,
        experiment_id: str,
        experiment_config: dict[str, Any],
    ) -> ExperimentStatus:
        """Update a draft experiment's config (PUT semantics, full replace).

        Only ``draft`` experiments can be updated. Once validated,
        launched, or paused, mutations are rejected with HTTP 400.
        """
        return self._request_model(
            "PUT", f"/oracle/experiments/{experiment_id}",
            ExperimentStatus,
            json=experiment_config,
        )

    def delete_experiment(self, experiment_id: str) -> ExperimentDeleted:
        """Delete an experiment.

        Deleting a launched / running experiment also cancels any
        in-flight child backtests.
        """
        return self._request_model(
            "DELETE", f"/oracle/experiments/{experiment_id}",
            ExperimentDeleted,
        )

    def validate_experiment(self, experiment_id: str) -> ExperimentValidation:
        """Validate a draft experiment.

        Required before ``launch_experiment`` will accept the call.
        Returns the config-check result — ``{valid, total_runs, errors,
        warnings}`` — NOT a {experiment_id, status} transition. Check
        ``valid`` and read ``total_runs`` before launching; ``errors``
        explains a ``valid: false`` (bad signal, params out of range, no
        entry filter, grid over cap).
        """
        return self._request_model(
            "POST", f"/oracle/experiments/{experiment_id}/validate",
            ExperimentValidation,
        )

    def launch_experiment(self, experiment_id: str) -> ExperimentStatus:
        """Fan out a validated experiment into individual backtests.

        Requires the experiment to be in ``validated`` status. Returns
        immediately with ``status: "launched"``; the actual fan-out
        progresses asynchronously — poll ``get_experiment(id)`` or
        ``list_results(experiment_id)`` to track completion.

        Bills: 1 unit per HTTP call (the fan-out children are not
        billed individually — phase-1 policy). x402: $0.25 per call.
        """
        return self._request_model(
            "POST", f"/oracle/experiments/{experiment_id}/launch",
            ExperimentStatus,
        )

    def pause_experiment(self, experiment_id: str) -> ExperimentStatus:
        """Pause a running experiment.

        Useful for stopping a fan-out mid-way without losing already-
        completed results. Resume via a follow-up ``launch_experiment``
        once paused.
        """
        return self._request_model(
            "POST", f"/oracle/experiments/{experiment_id}/pause",
            ExperimentStatus,
        )

    # ------------------------------------------------------------------ #
    # Results (paginated backtest results across experiments)
    # ------------------------------------------------------------------ #
    def list_results(
        self,
        *,
        experiment_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> OracleResultsPage:
        """Read backtest results materializing under an experiment, or
        across the full corpus when ``experiment_id`` is omitted.

        Args:
            experiment_id: Optional — when provided, scopes results to a
                single experiment. When omitted, returns the broader
                cross-experiment view paginated by ``limit`` / ``offset``.
            limit: Page size, max 500 (server-enforced).
            offset: Pagination offset.

        Returns:
            ``OracleResultsPage`` with ``total``, ``offset``, ``limit``,
            and ``results`` (list of wide-format result dicts).

        Note:
            Pre-Oracle v0.14.7 the unfiltered call 500'd because the BQ
            ORDER BY fell through a DuckDB-quoted-identifier fallback
            that BQ rejected. Fixed in MangroveOracle PR #237.
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if experiment_id is not None:
            params["experiment_id"] = experiment_id
        return self._request_model(
            "GET", "/oracle/results",
            OracleResultsPage,
            params=params,
        )

    # ------------------------------------------------------------------ #
    # Metadata catalogs (free / non-billable)
    # ------------------------------------------------------------------ #
    def list_datasets(self) -> list[dict[str, Any]]:
        """List the OHLCV datasets the engine can run experiments against.

        Each dict carries ``asset``, ``timeframe``, ``file``, ``hash``,
        ``rows``, ``start_date``, ``end_date``. Curated, immutable
        snapshots — referenced by ``experiment_config.datasets``.
        """
        return self._request("GET", "/oracle/datasets")

    def list_signals(self) -> list[dict[str, Any]]:
        """List the signals (entry triggers / filters / exit triggers)
        available to experiments.

        Each dict carries ``name``, ``type`` (``TRIGGER`` / ``FILTER``),
        ``params`` (typed param spec for each tunable), ``constraints``,
        ``description``, ``requires`` (OHLCV columns needed), and
        ``category``. Use this to discover valid signal names + param
        ranges when constructing an ``ExperimentConfig`` programmatically.
        """
        return self._request("GET", "/oracle/signals")

    def list_templates(self) -> list[dict[str, Any]]:
        """List predefined strategy templates you can seed an experiment from."""
        return self._request("GET", "/oracle/templates")

    # ------------------------------------------------------------------ #
    # Execution-config defaults (canonical trading defaults snapshot)
    # ------------------------------------------------------------------ #
    def exec_config_defaults(self) -> dict[str, Any]:
        """Fetch the canonical execution-defaults snapshot.

        Returns the flattened trading-defaults dict: risk management
        (``max_risk_per_trade``, ``reward_factor``, ``position_size_calc``),
        position limits (``initial_balance``, ``max_open_positions``,
        ``min_trade_amount``, ...), volatility settings, trading rules
        (``cooldown_bars``, ``max_hold_time_hours``), and time-based
        exits. Use these to seed an ``ExperimentConfig`` or as input
        validation bounds when authoring a strategy programmatically.

        Endpoint: GET /oracle/exec-config/defaults
        """
        return self._request("GET", "/oracle/exec-config/defaults")

    # ------------------------------------------------------------------ #
    # Simulate (single-strategy run without persisting)
    # ------------------------------------------------------------------ #
    def simulate_run(self, request: dict[str, Any]) -> SimulateRunResponse:
        """Run a single strategy in interactive mode without persisting.

        Use this for "try this rule and see" loops where you don't want
        the result to land in the experiment store. For batched / sweep
        scoring, use ``create_experiment`` + ``launch_experiment``.

        Args:
            request: Simulate request body — at minimum ``strategy``
                (a dict in MangroveAI strategy_json shape), ``asset``,
                ``timeframe``, ``dataset_id``. See
                ``simulate_presets()`` for ready-made templates.

        Returns:
            ``SimulateRunResponse`` with ``simulation_id``, ``status``,
            ``result`` (the wide-format backtest row), and optional
            ``error`` field for server-side rejections.

        Endpoint: POST /oracle/simulate/run
        """
        return self._request_model(
            "POST", "/oracle/simulate/run",
            SimulateRunResponse,
            json=request,
        )

    def simulate_generate(self, request: dict[str, Any]) -> dict[str, Any]:
        """Generate a strategy candidate from a high-level intent (LLM-backed).

        Endpoint: POST /oracle/simulate/generate
        """
        return self._request("POST", "/oracle/simulate/generate", json=request)

    def simulate_presets(self) -> list[dict[str, Any]]:
        """List ready-made simulate request templates.

        Endpoint: GET /oracle/simulate/presets
        """
        return self._request("GET", "/oracle/simulate/presets")

    def simulate_history(self, *, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """List recent simulate runs (caller-scoped).

        Endpoint: GET /oracle/simulate/history
        """
        return self._request(
            "GET", "/oracle/simulate/history",
            params={"limit": limit, "offset": offset},
        )

    # ------------------------------------------------------------------ #
    # Leaderboard (curated personas — display roster, NOT strategy ranking)
    # ------------------------------------------------------------------ #
    def leaderboard(self) -> LeaderboardResponse:
        """Return the curated leaderboard persona roster.

        Personas are display wrappers for the public dashboard at
        mangrovedeveloper.ai/leaderboard. Each persona's
        ``deployed_strategy_ids`` link to the per-strategy live state
        readable via ``list_deployed_strategies()`` /
        ``get_deployed_strategy_state()``.

        This is NOT a strategy-ranking endpoint — for the
        best-performing-strategies view, query ``list_results()`` with
        an appropriate ``sort`` parameter.

        Endpoint: GET /oracle/leaderboard
        """
        return self._request_model("GET", "/oracle/leaderboard", LeaderboardResponse)

    # ------------------------------------------------------------------ #
    # Deployed strategies (live execution state of curated deployed strategies)
    # ------------------------------------------------------------------ #
    def list_deployed_strategies(self) -> list[DeployedStrategy]:
        """List curated strategies currently running in paper-trading mode.

        Each entry carries identity + live execution state
        (account_value, cash_balance, num_open_positions, total_trades,
        status). Pair with ``leaderboard()`` to map strategies back to
        their owning persona.

        Endpoint: GET /oracle/deployed/strategies
        """
        data = self._request("GET", "/oracle/deployed/strategies")
        # Server returns {"strategies": [...]} or a bare list depending
        # on Oracle version. Accept both shapes.
        if isinstance(data, dict) and "strategies" in data:
            items = data["strategies"]
        else:
            items = data
        return [DeployedStrategy.model_validate(item) for item in (items or [])]

    def get_deployed_strategy_state(self, strategy_id: str) -> dict[str, Any]:
        """Read the live execution state of one deployed strategy.

        Endpoint: GET /oracle/deployed/{strategy_id}/state
        """
        return self._request("GET", f"/oracle/deployed/{strategy_id}/state")

    def get_deployed_strategy_events(
        self,
        strategy_id: str,
        *,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Read recent trade events for one deployed strategy.

        Args:
            strategy_id: The deployed strategy ID.
            limit: Number of events to return (1-500, server-enforced).

        Endpoint: GET /oracle/deployed/{strategy_id}/events
        """
        return self._request(
            "GET", f"/oracle/deployed/{strategy_id}/events",
            params={"limit": limit},
        )
