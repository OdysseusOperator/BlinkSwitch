#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${BLINKSWITCH_IN_NIX:-}" != "1" && -f "$SCRIPT_DIR/flake.nix" && -n "$(command -v nix || true)" ]]; then
    exec nix develop "$SCRIPT_DIR" --command env BLINKSWITCH_IN_NIX=1 "$SCRIPT_DIR/start.sh" "$@"
fi

# NixOS exposes the active GPU drivers outside the development shell's libraries.
# Keep this after nix develop, which sets its own LD_LIBRARY_PATH.
if [[ -d /run/opengl-driver/lib ]]; then
    export LD_LIBRARY_PATH="/run/opengl-driver/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: uv is required; install it from https://docs.astral.sh/uv/" >&2
    exit 1
fi

VENV_DIR="$SCRIPT_DIR/.venv"
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "Creating shared Python environment..."
    if [[ "${BLINKSWITCH_IN_NIX:-}" == "1" ]]; then
        # Use the host Python on NixOS so its glibc matches the active GPU drivers.
        # The pinned development shell can have an older, incompatible glibc.
        PYTHON_BIN="$(command -v python3)"
        if [[ -x /run/current-system/sw/bin/python3 ]]; then
            PYTHON_BIN=/run/current-system/sw/bin/python3
        fi
        uv venv "$VENV_DIR" --python "$PYTHON_BIN" --no-python-downloads
    else
        uv venv "$VENV_DIR" --python 3.11
    fi
fi

BLINKSWITCH_VENV="$VENV_DIR" exec "$VENV_DIR/bin/python" "$SCRIPT_DIR/scripts/start_blinkswitch.py" "$@"
