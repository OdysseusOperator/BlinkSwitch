#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "${WAYLAND_DISPLAY:-}" ]]; then
    printf 'ERROR: Native Wayland testing requires a running Wayland session.\n' >&2
    exit 1
fi

export BLINKSWITCH_RENDER_CHECK=1

printf 'Native Wayland scaling test: look for RENDER CHECK PASS in terminal.\n'
printf 'Border should touch every window edge; compare at different display scales and after resizing.\n'
exec "$SCRIPT_DIR/start_blinkswitch_new.sh" "$@"
