#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export BLINKSWITCH_KEEP_OPEN=1

"$SCRIPT_DIR/frontend-go/build.sh"
exec "$SCRIPT_DIR/start.sh" --frontend clay "$@"
