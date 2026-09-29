#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${BLINKSWITCH_IN_NIX:-}" != "1" && -f "$SCRIPT_DIR/flake.nix" && -n "$(command -v nix || true)" ]]; then
    exec nix develop "$SCRIPT_DIR" --command env BLINKSWITCH_IN_NIX=1 "$SCRIPT_DIR/start.sh" "$@"
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: uv is required; install it from https://docs.astral.sh/uv/" >&2
    exit 1
fi

if [[ ! -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
    echo "Creating shared Python environment..."
    uv venv "$SCRIPT_DIR/.venv" --python 3.11
fi

exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/scripts/start_blinkswitch.py" "$@"
