"""Claude Code 훅 이벤트를 받아 공유 status.json에 에이전트 상태를 기록한다."""
import json
import sys

from status_store import write_status


def main() -> None:
    status_file, agent_id = sys.argv[1], sys.argv[2]
    payload = json.loads(sys.stdin.read())

    event = payload.get("hook_event_name", "")
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})

    if event == "SessionStart":
        status, detail = "idle", "세션 시작"
    elif event == "UserPromptSubmit":
        status, detail = "thinking", "요청 처리 중"
    elif event == "PreToolUse":
        status = "working"
        if tool_name == "Bash":
            command = str(tool_input.get("command", ""))[:60]
            detail = f"실행: {command}"
        else:
            detail = f"{tool_name} 사용 중"
    elif event == "Stop":
        status, detail = "idle", "응답 완료, 대기 중"
    elif event == "SessionEnd":
        status, detail = "offline", "세션 종료"
    else:
        status, detail = "unknown", event

    write_status(status_file, agent_id, status, detail)


if __name__ == "__main__":
    main()
