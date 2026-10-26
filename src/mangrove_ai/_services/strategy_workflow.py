"""Thin REST adapter to the exact operations used by Michael and MCP.

No skill bodies, composition rules, candidate ranking or lifecycle policy live here.
"""
from typing import Any

from ..models.strategy_workflow import SavedStrategy, SaveStrategyRequest, SkillDocument
from ._base import BaseService


class StrategyWorkflowService(BaseService):
    def load_skill(self, skill: str, *, section: str | None = None,
                   resource: str | None = None) -> SkillDocument:
        body = {"skill": skill}
        if section is not None:
            body["section"] = section
        if resource is not None:
            body["resource"] = resource
        return self._request_model("POST", "/strategy-workflow/load_skill", SkillDocument, json=body)

    def save_strategy(self, request: SaveStrategyRequest) -> SavedStrategy:
        return self._request_model("POST", "/strategy-workflow/save_strategy", SavedStrategy,
                                   json=request.model_dump(exclude_none=True))

    def update_strategy(self, strategy_id: str, *, entry_signals: list[dict[str, Any]] | None = None,
                        exit_signals: list[dict[str, Any]] | None = None,
                        **options: Any) -> dict[str, Any]:
        body = {"strategy_id": strategy_id, **options}
        if entry_signals is not None:
            body["entry_signals"] = entry_signals
        if exit_signals is not None:
            body["exit_signals"] = exit_signals
        return self._request("POST", "/strategy-workflow/update_strategy", json=body)

    def get_strategy(self, strategy_id: str) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/get_strategy", json={"strategy_id": strategy_id})

    def list_strategies(self, *, limit: int = 20) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/list_strategies", json={"limit": limit})

    def verify_strategy(self, strategy_id: str) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/verify_strategy", json={"strategy_id": strategy_id})

    def get_execution_config_schema(self) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/get_execution_config_schema", json={})

    def screen_candidates(self, asset: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/screen_candidates",
                             json={"asset": asset, "candidates": candidates})

    def run_backtest(self, strategy_id: str, start_date: str, end_date: str,
                     **options: Any) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/run_backtest", json={
            "strategy_id": strategy_id, "start_date": start_date, "end_date": end_date, **options})

    def get_backtest(self, backtest_id: str) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/get_backtest", json={"backtest_id": backtest_id})

    def list_backtests(self, *, strategy_id: str | None = None, limit: int = 20) -> dict[str, Any]:
        body: dict[str, Any] = {"limit": limit}
        if strategy_id is not None:
            body["strategy_id"] = strategy_id
        return self._request("POST", "/strategy-workflow/list_backtests", json=body)

    def get_backtest_trades(self, backtest_id: str, *, offset: int = 0,
                            limit: int = 100) -> dict[str, Any]:
        """One page of a backtest's simulated trades (at most 500 per call).

        Page with ``offset`` until ``offset + len(trades)`` reaches ``trade_count``.
        """
        return self._request("POST", "/strategy-workflow/get_backtest_trades", json={
            "backtest_id": backtest_id, "offset": offset, "limit": limit})

    def list_backtest_markets(self, asset: str) -> dict[str, Any]:
        """The markets ``asset`` can be backtested on, as the engine supports them."""
        return self._request("POST", "/strategy-workflow/list_backtest_markets",
                             json={"asset": asset})

    def build_strategy_for_regime(self, asset: str,
                                  candle_size: str | None = None) -> dict[str, Any]:
        """Run the Strategy Engine route: pick a completed run for the current regime,
        save it and backtest it on current data.

        The server fixes the regime, the floors, the pick and the backtest window; only
        the asset, and the candle size when one is wanted, are sent.
        """
        body: dict[str, Any] = {"asset": asset}
        if candle_size:
            body["candle_size"] = candle_size
        return self._request("POST", "/strategy-workflow/build_strategy_for_regime", json=body)

    def find_sweep_runs(self, sort_by: str, **filters: Any) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/find_sweep_runs",
                             json={"sort_by": sort_by, **filters})

    def list_sweep_markets(self, **filters: Any) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/list_sweep_markets", json=filters)

    def size_sweep(self, **options: Any) -> dict[str, Any]:
        """Ask the server to size a search without creating or launching it."""
        return self._request("POST", "/strategy-workflow/size_sweep", json=options)

    def get_sweep_limits(self) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/get_sweep_limits", json={})

    def create_sweep(self, sweep_name: str, **options: Any) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/create_sweep",
                             json={"sweep_name": sweep_name, **options})

    def launch_sweep(self, experiment_id: str) -> dict[str, Any]:
        """Launch the agreed search through the canonical server operation."""
        return self._request("POST", "/strategy-workflow/launch_sweep",
                             json={"experiment_id": experiment_id})

    def get_sweep(self, experiment_id: str) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/get_sweep",
                             json={"experiment_id": experiment_id})

    def list_sweeps(self, **options: Any) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/list_sweeps", json=options)

    def list_run_filters(self, experiment_id: str) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/list_run_filters",
                             json={"experiment_id": experiment_id})

    def get_sweep_run(self, experiment_id: str, run_index: int,
                      *, config_hash: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"experiment_id": experiment_id, "run_index": run_index}
        if config_hash is not None:
            body["config_hash"] = config_hash
        return self._request("POST", "/strategy-workflow/get_sweep_run", json=body)

    def pause_sweep(self, experiment_id: str) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/pause_sweep",
                             json={"experiment_id": experiment_id})

    def search_marketplace(self, **filters: Any) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/search_marketplace", json=filters)

    def get_marketplace_strategy(self, strategy_id: str) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/get_marketplace_strategy",
                             json={"strategy_id": strategy_id})
