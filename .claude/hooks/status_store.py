"""~/.my-ai-team-office/status.json에 대한 파일 락 기반 read-modify-write 공유 로직."""
from __future__ import annotations

import fcntl
import json
from datetime import datetime, timezone


def write_status(status_file: str, agent_id: str, status: str, detail: str) -> None:
    """status_file의 agent_id 항목을 status/detail로 갱신한다 (동시 쓰기 안전)."""
    entry = {
        "status": status,
        "detail": detail,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    with open(status_file, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        raw = f.read()
        data = json.loads(raw) if raw.strip() else {}
        data[agent_id] = entry
        f.seek(0)
        f.truncate()
        json.dump(data, f, ensure_ascii=False, indent=2)
        fcntl.flock(f, fcntl.LOCK_UN)
