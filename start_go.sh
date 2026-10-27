#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

UPDATE_ARGS=()
TOGGLE=0
for argument in "$@"; do
    case "$argument" in
        --update)
            UPDATE_ARGS=(--update)
            ;;
        --keep-open)
            export BLINKSWITCH_KEEP_OPEN=1
            ;;
        --render-check)
            export BLINKSWITCH_RENDER_CHECK=1
            ;;
        --toggle)
            TOGGLE=1
            ;;
        -h|--help)
            printf '%s\n' \
                'Usage: ./start_go.sh [--update] [--keep-open] [--render-check]' \
                '       ./start_go.sh --toggle' \
                '' \
                'Rebuild the Go frontend and start it with the backend.' \
                '  --update        Refresh shared Python dependencies.' \
                '  --keep-open     Show immediately and stay open; skip hotkey/toggle registration.' \
                '  --render-check  Enable native Wayland scaling diagnostics.' \
                '  --toggle        Toggle an already-running Go frontend without building or starting services.'
            exit 0
            ;;
        *)
            printf 'ERROR: Unknown argument: %s (see --help)\n' "$argument" >&2
            exit 2
            ;;
    esac
done

if [[ "$TOGGLE" == "1" ]]; then
    exec "$SCRIPT_DIR/frontend-go/blinkswitch-frontend" --toggle
fi

if [[ "${BLINKSWITCH_RENDER_CHECK:-}" == "1" ]]; then
    if [[ -z "${WAYLAND_DISPLAY:-}" ]]; then
        printf 'ERROR: Render checks require a running Wayland session.\n' >&2
        exit 1
    fi
    printf 'Native Wayland scaling test: look for RENDER CHECK PASS in terminal.\n'
    printf 'Border should touch every window edge; compare after resizing or changing display scale.\n'
fi

"$SCRIPT_DIR/frontend-go/build.sh"
exec "$SCRIPT_DIR/start.sh" --frontend clay "${UPDATE_ARGS[@]}"
