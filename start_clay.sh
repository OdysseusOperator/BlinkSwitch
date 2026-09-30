#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export BLINKSWITCH_FRONTEND=clay

if [[ "${1:-}" == "--toggle" ]]; then
    exec "$SCRIPT_DIR/frontend-go/blinkswitch-frontend" --toggle
fi

exec "$SCRIPT_DIR/start.sh" "$@"
