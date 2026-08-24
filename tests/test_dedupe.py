from datetime import datetime, timezone

from collector.dedupe import deduplicate
from collector.models import NormalizedItem


def make_item(id_: str, title: str = "title") -> NormalizedItem:
    return NormalizedItem(
        id=id_,
        source="hackernews",
        title=title,
        url=f"https://example.com/{id_}",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_deduplicate_empty_list_returns_empty_list():
    assert deduplicate([]) == []


def test_deduplicate_no_duplicates_returns_all_items_unchanged():
    items = [make_item("a"), make_item("b"), make_item("c")]
    assert deduplicate(items) == items


def test_deduplicate_keeps_first_occurrence_within_batch():
    first = make_item("a", title="first")
    second = make_item("a", title="second")
    result = deduplicate([first, second])
    assert result == [first]


def test_deduplicate_excludes_items_already_in_seen_ids():
    items = [make_item("a"), make_item("b")]
    result = deduplicate(items, seen_ids={"a"})
    assert result == [items[1]]


def test_deduplicate_preserves_original_order():
    items = [make_item("c"), make_item("a"), make_item("b")]
    result = deduplicate(items)
    assert [item.id for item in result] == ["c", "a", "b"]


def test_deduplicate_does_not_mutate_seen_ids_argument():
    seen_ids = {"a"}
    deduplicate([make_item("a"), make_item("b")], seen_ids=seen_ids)
    assert seen_ids == {"a"}
