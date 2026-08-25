"""~/.my-ai-team-office를 정적 서빙하고 POST /run으로 파이프라인을 실행하는 로컬 서버.

표준 라이브러리만 사용 (외부 의존성 없음).

실행: python scripts/office_server.py
"""
from __future__ import annotations

import json
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

PORT = 8787
OFFICE_DIR = Path.home() / ".my-ai-team-office"
REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
PIPELINE_SCRIPT = REPO_ROOT / "scripts" / "run_pipeline.py"
LOG_FILE = OFFICE_DIR / "last_run.log"

_pipeline_process: subprocess.Popen[bytes] | None = None
_pipeline_lock = threading.Lock()


def _is_pipeline_running() -> bool:
    return _pipeline_process is not None and _pipeline_process.poll() is None


def _start_pipeline() -> bool:
    global _pipeline_process
    with _pipeline_lock:
        if _is_pipeline_running():
            return False
        OFFICE_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "w", encoding="utf-8") as log_file:
            _pipeline_process = subprocess.Popen(
                [str(VENV_PYTHON), str(PIPELINE_SCRIPT)],
                cwd=str(REPO_ROOT),
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
        return True


class OfficeRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(OFFICE_DIR), **kwargs)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/run":
            self._send_json({"error": "not found"}, status=404)
            return
        if _start_pipeline():
            self._send_json({"started": True})
        else:
            self._send_json({"started": False, "reason": "already running"})


def main() -> None:
    OFFICE_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("localhost", PORT), OfficeRequestHandler)
    print(f"serving {OFFICE_DIR} on http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
