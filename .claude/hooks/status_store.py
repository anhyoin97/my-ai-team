"""~/.my-ai-team-office/status.json에 대한 파일 락 기반 read-modify-write 공유 로직."""
from __future__ import annotations

import fcntl
import json
from datetime import datetime, timedelta, timezone
from typing import Any

_STALE_AFTER = timedelta(hours=12)


def write_status(status_file: str, agent_id: str, status: str, detail: str) -> None:
    """status_file의 agent_id 항목을 status/detail로 갱신한다 (동시 쓰기 안전).

    기록할 때마다 updated_at이 12시간 넘게 지난 다른 항목은 좀비 에이전트로 보고 함께 제거한다.
    """
    now = datetime.now(timezone.utc)
    entry = {
        "status": status,
        "detail": detail,
        "updated_at": now.isoformat(timespec="seconds"),
    }

    with open(status_file, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        raw = f.read()
        data = json.loads(raw) if raw.strip() else {}
        data = {
            existing_id: existing_entry
            for existing_id, existing_entry in data.items()
            if not _is_stale(existing_entry, now)
        }
        data[agent_id] = entry
        f.seek(0)
        f.truncate()
        json.dump(data, f, ensure_ascii=False, indent=2)
        fcntl.flock(f, fcntl.LOCK_UN)


def _is_stale(entry: dict[str, Any], now: datetime) -> bool:
    try:
        updated_at = datetime.fromisoformat(entry["updated_at"])
    except (KeyError, TypeError, ValueError):
        return False
    return now - updated_at > _STALE_AFTER
