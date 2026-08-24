#!/usr/bin/env bash
set -euo pipefail

INPUT="$(cat)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATUS_DIR="$HOME/.my-ai-team-office"
STATUS_FILE="$STATUS_DIR/status.json"
mkdir -p "$STATUS_DIR"

AGENT_ID="$(basename "${CLAUDE_PROJECT_DIR:-$(pwd)}")"

python3 "$SCRIPT_DIR/report_status.py" "$STATUS_FILE" "$AGENT_ID" <<< "$INPUT"
exit 0
