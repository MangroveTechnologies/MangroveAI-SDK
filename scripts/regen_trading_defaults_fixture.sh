#!/usr/bin/env bash
# Regenerate tests/fixtures/trading_defaults_response.json from live MangroveAI canon.
# Run after any MangroveAI canon update to keep the SDK fixture aligned.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
URL="${MANGROVE_API_BASE:-https://api.mangrovedeveloper.ai}/api/v1/config/trading-defaults"
echo "fetching canon from $URL"
curl -sS "$URL" | python3 -m json.tool > "$REPO_ROOT/tests/fixtures/trading_defaults_response.json"
echo "fixture regenerated. diff:"
git -C "$REPO_ROOT" --no-pager diff --stat tests/fixtures/trading_defaults_response.json
