"""SQLite 이력 저장소: 수집 항목과 다이제스트 발행 이력을 축적한다."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from collector.models import NormalizedItem

_ITEMS_TABLE = """
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    published_at TEXT NOT NULL,
    summary TEXT NOT NULL,
    score REAL NOT NULL,
    keywords_matched TEXT NOT NULL,
    first_seen_at TEXT NOT NULL
)
"""

_DIGESTS_TABLE = """
CREATE TABLE IF NOT EXISTS digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_at TEXT NOT NULL,
    item_count INTEGER NOT NULL,
    file_path TEXT NOT NULL
)
"""


def init_db(db_path: str) -> None:
    """items/digests 테이블이 없으면 생성한다. 여러 번 호출해도 안전하다."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(_ITEMS_TABLE)
        conn.execute(_DIGESTS_TABLE)


def get_seen_ids(db_path: str) -> set[str]:
    """items 테이블에 저장된 모든 id를 반환한다."""
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT id FROM items").fetchall()
    return {row[0] for row in rows}


def save_items(db_path: str, items: list[NormalizedItem]) -> int:
    """새 항목만 삽입하고, 새로 삽입된 개수를 반환한다. 이미 있는 id는 조용히 무시한다."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.executemany(
            """
            INSERT OR IGNORE INTO items
                (id, source, title, url, published_at, summary, score,
                 keywords_matched, first_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.id,
                    item.source,
                    item.title,
                    item.url,
                    item.published_at.isoformat(),
                    item.summary,
                    item.score,
                    json.dumps(item.keywords_matched),
                    datetime.now().isoformat(),
                )
                for item in items
            ],
        )
        return cursor.rowcount if cursor.rowcount != -1 else 0


def record_digest(
    db_path: str,
    items: list[NormalizedItem],
    file_path: str,
    generated_at: datetime,
) -> int:
    """digests 테이블에 발행 이력을 기록하고 새로 생긴 row id를 반환한다."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO digests (generated_at, item_count, file_path) VALUES (?, ?, ?)",
            (generated_at.isoformat(), len(items), file_path),
        )
        row_id = cursor.lastrowid
        assert row_id is not None
        return row_id
