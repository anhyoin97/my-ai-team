import json
import sqlite3
from datetime import datetime, timezone

from collector.models import NormalizedItem
from collector.storage import get_seen_ids, init_db, record_digest, save_items


def make_item(id_: str = "abc123", title: str = "title", **kwargs: object) -> NormalizedItem:
    defaults: dict[str, object] = {
        "id": id_,
        "source": "test",
        "title": title,
        "url": f"https://example.com/{id_}",
        "published_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "summary": "summary",
        "keywords_matched": ["python"],
        "score": 1.0,
    }
    defaults.update(kwargs)
    return NormalizedItem(**defaults)  # type: ignore[arg-type]


def test_init_db_is_idempotent(tmp_path):
    db_path = str(tmp_path / "history.db")
    init_db(db_path)
    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
    assert {"items", "digests"} <= tables


def test_get_seen_ids_empty_when_no_items(tmp_path):
    db_path = str(tmp_path / "history.db")
    init_db(db_path)

    assert get_seen_ids(db_path) == set()


def test_save_items_reflected_in_get_seen_ids(tmp_path):
    db_path = str(tmp_path / "history.db")
    init_db(db_path)
    items = [make_item("a"), make_item("b")]

    inserted = save_items(db_path, items)

    assert inserted == 2
    assert get_seen_ids(db_path) == {"a", "b"}


def test_save_items_ignores_duplicates(tmp_path):
    db_path = str(tmp_path / "history.db")
    init_db(db_path)
    item = make_item("a")

    first = save_items(db_path, [item])
    second = save_items(db_path, [item])

    assert first == 1
    assert second == 0
    assert get_seen_ids(db_path) == {"a"}


def test_save_items_stores_keywords_matched_as_json(tmp_path):
    db_path = str(tmp_path / "history.db")
    init_db(db_path)
    item = make_item("a", keywords_matched=["python", "rust"])

    save_items(db_path, [item])

    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT keywords_matched FROM items WHERE id = ?", ("a",)).fetchone()
    assert json.loads(row[0]) == ["python", "rust"]


def test_record_digest_inserts_row_and_returns_id(tmp_path):
    db_path = str(tmp_path / "history.db")
    init_db(db_path)
    items = [make_item("a"), make_item("b")]
    generated_at = datetime(2026, 1, 5, tzinfo=timezone.utc)

    row_id = record_digest(db_path, items, "digests/2026-01-05.md", generated_at)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT generated_at, item_count, file_path FROM digests WHERE id = ?", (row_id,)
        ).fetchone()
    assert row[1] == 2
    assert row[2] == "digests/2026-01-05.md"


def test_record_digest_multiple_calls_get_distinct_ids(tmp_path):
    db_path = str(tmp_path / "history.db")
    init_db(db_path)
    generated_at = datetime(2026, 1, 5, tzinfo=timezone.utc)

    first_id = record_digest(db_path, [], "digests/first.md", generated_at)
    second_id = record_digest(db_path, [], "digests/second.md", generated_at)

    assert first_id != second_id
