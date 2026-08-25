"""~/.my-ai-team-office를 정적 서빙하고 POST /run으로 파이프라인을 실행하는 로컬 서버.

표준 라이브러리만 사용 (외부 의존성 없음).

실행: python scripts/office_server.py
"""
from __future__ import annotations

import json
import subprocess
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

PORT = 8787
OFFICE_DIR = Path.home() / ".my-ai-team-office"
REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
PIPELINE_SCRIPT = REPO_ROOT / "scripts" / "run_pipeline.py"
LOG_FILE = OFFICE_DIR / "last_run.log"
DIGESTS_DIR = REPO_ROOT / "output" / "digests"

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

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/digests":
            self._send_digest_list()
            return
        if path.startswith("/digests/"):
            self._send_digest_file(path[len("/digests/") :])
            return
        super().do_GET()

    def _send_digest_list(self) -> None:
        if not DIGESTS_DIR.is_dir():
            self._send_json([])
            return
        files = sorted(
            (p for p in DIGESTS_DIR.iterdir() if p.is_file() and p.suffix == ".md"),
            key=lambda p: p.name,
            reverse=True,
        )
        payload = [
            {
                "filename": p.name,
                "created_at": datetime.fromtimestamp(
                    p.stat().st_mtime, tz=timezone.utc
                ).isoformat(timespec="seconds"),
            }
            for p in files
        ]
        self._send_json(payload)

    def _send_digest_file(self, raw_filename: str) -> None:
        filename = unquote(raw_filename)
        if not filename or "/" in filename or "\\" in filename or ".." in filename:
            self._send_json({"error": "invalid filename"}, status=400)
            return

        target = (DIGESTS_DIR / filename).resolve()
        try:
            target.relative_to(DIGESTS_DIR.resolve())
        except ValueError:
            self._send_json({"error": "invalid filename"}, status=400)
            return

        if not target.is_file():
            self._send_json({"error": "not found"}, status=404)
            return

        body = target.read_text(encoding="utf-8").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
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
