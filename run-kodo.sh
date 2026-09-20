#!/bin/bash
# Starts Kodo's backend and frontend, each in its own Terminal window, then
# opens the app in your browser. macOS only (uses Terminal.app + `open`).
#
# Self-locating: KODO_DIR is derived from this script's own location, so it
# works right after cloning with no path editing - as long as this file
# stays at the repo root, next to backend/ and frontend/. Override the
# variables below only if your layout differs from that.

set -e

KODO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$KODO_DIR/backend"      # <- override if backend/ lives elsewhere
FRONTEND_DIR="$KODO_DIR/frontend"    # <- override if frontend/ lives elsewhere
FRONTEND_URL="http://localhost:5173" # <- override if you changed the Vite port
STARTUP_WAIT_SECONDS=4               # <- bump this if your machine boots slower

osascript <<EOF
tell application "Terminal"
    activate
    do script "cd \"$BACKEND_DIR\" && source .venv/bin/activate && uvicorn app.main:app --reload"
    do script "cd \"$FRONTEND_DIR\" && npm run dev"
end tell
EOF

sleep "$STARTUP_WAIT_SECONDS"
open "$FRONTEND_URL"
