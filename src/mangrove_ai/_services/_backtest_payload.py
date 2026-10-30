from __future__ import annotations

from ..models._base import MangroveModel


def backtest_payload(request: MangroveModel) -> dict:
    """Send risk options where the engine reads them, preserving explicit nulls."""
    payload = request.model_dump(exclude_none=True)
    for key in ("cooldown_model", "max_drawdown_limit", "max_drawdown_halt_limit", "cooldown_config"):
        payload.pop(key, None)
        if key in request.model_fields_set:
            value = getattr(request, key)
            if key == "cooldown_config" and value is None:
                continue
            config = payload.setdefault("execution_config", {})
            if key in config and config[key] != value:
                raise ValueError(f"{key} conflicts with execution_config.{key}")
            config[key] = value
    return payload
