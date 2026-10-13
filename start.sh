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

VENV_DIR="$SCRIPT_DIR/.venv-uv"
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "Creating shared Python environment..."
    uv venv "$VENV_DIR" --python 3.11
fi

BLINKSWITCH_VENV="$VENV_DIR" exec "$VENV_DIR/bin/python" "$SCRIPT_DIR/scripts/start_blinkswitch.py" "$@"
