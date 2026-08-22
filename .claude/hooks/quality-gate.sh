#!/usr/bin/env bash
set -euo pipefail

INPUT="$(cat)"

COMMAND="$(python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
print(data.get('tool_input', {}).get('command', ''))
" <<< "$INPUT")"

# git commit이 아니면 그냥 통과
if ! echo "$COMMAND" | grep -Eq '(^|[;&|])[[:space:]]*git[[:space:]]+commit\b'; then
    exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$PROJECT_DIR"

VENV_PY="$PROJECT_DIR/.venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
    echo "품질 게이트: .venv가 없습니다. venv를 먼저 만드세요." >&2
    exit 2
fi

echo "품질 게이트: git commit 감지 — ruff/mypy/pytest 실행 중..." >&2

if ! "$VENV_PY" -m ruff check .; then
    echo "품질 게이트 실패: ruff check 오류. 커밋이 차단되었습니다." >&2
    exit 2
fi

if ! "$VENV_PY" -m mypy src; then
    echo "품질 게이트 실패: mypy 타입 오류. 커밋이 차단되었습니다." >&2
    exit 2
fi

if ! "$VENV_PY" -m pytest -q; then
    echo "품질 게이트 실패: pytest 실패. 커밋이 차단되었습니다." >&2
    exit 2
fi

echo "품질 게이트 통과. 커밋을 진행합니다." >&2
exit 0
