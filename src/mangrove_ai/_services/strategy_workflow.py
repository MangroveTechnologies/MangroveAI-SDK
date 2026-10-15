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
        return self._request("POST", "/strategy-workflow/screen_candidates", json={"asset": asset, "candidates": candidates})

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

    def build_strategy_for_regime(self, asset: str, timeframe: str) -> dict[str, Any]:
        """Find, save and backtest the proven strategy for the current regime.

        The server fixes the regime, the quality filters and the backtest window; only the
        asset and timeframe are sent.
        """
        return self._request("POST", "/strategy-workflow/build_strategy_for_regime",
                             json={"asset": asset, "timeframe": timeframe})

    def find_sweep_runs(self, sort_by: str, **filters: Any) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/find_sweep_runs",
                             json={"sort_by": sort_by, **filters})

    def search_marketplace(self, **filters: Any) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/search_marketplace", json=filters)

    def get_marketplace_strategy(self, strategy_id: str) -> dict[str, Any]:
        return self._request("POST", "/strategy-workflow/get_marketplace_strategy",
                             json={"strategy_id": strategy_id})
