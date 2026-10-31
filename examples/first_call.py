"""Read usage with an installed MangroveAI SDK and private JSON configuration.

Run: python examples/first_call.py /absolute/path/to/private-config.json
Config keys: api_key (required), base_url (optional, ending in /api/v1).
No strategy, backtest, order, payment, or MCP tool is invoked.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mangrove_ai import APIError, MangroveAI, MangroveSDKError


def read_usage(config_path: Path) -> dict[str, int | None]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or not isinstance(config.get("api_key"), str) or not config["api_key"]:
        raise ValueError("Private configuration requires a nonempty api_key.")
    with MangroveAI(
        api_key=config["api_key"], base_url=config.get("base_url"),
        load_dotenv=False, timeout=15, auto_retry=False,
    ) as client:
        metrics = client.users.get_my_metrics()
    return {
        "conversations_count": metrics.conversations_count,
        "messages_count": metrics.messages_count,
        "strategies_count": metrics.strategies_count,
        "backtests_count": metrics.backtests_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="Private JSON file outside the repository")
    args = parser.parse_args()
    try:
        result = read_usage(args.config)
    except APIError as exc:
        # Do not print arbitrary server messages or configuration values.
        print(json.dumps({"status": "api_error", "http_status": exc.status_code, "retry_after": exc.retry_after}))
        return 1
    except (OSError, ValueError, MangroveSDKError):
        print(json.dumps({"status": "error", "message": "Check private configuration, connectivity, and API access."}))
        return 1
    print(json.dumps({"status": "ok", "metrics": result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
