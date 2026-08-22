from datetime import datetime, timezone

from collector.models import NormalizedItem, RawItem, compute_item_id


def test_compute_item_id_is_stable_and_ignores_trailing_slash_and_case():
    id_a = compute_item_id("https://example.com/Post/1/")
    id_b = compute_item_id("https://example.com/post/1")
    assert id_a == id_b


def test_compute_item_id_differs_for_different_urls():
    assert compute_item_id("https://example.com/a") != compute_item_id("https://example.com/b")


def test_normalized_item_from_raw_fills_defaults():
    raw = RawItem(source="hackernews", title="  Hello World  ", url="https://example.com/x")
    item = NormalizedItem.from_raw(raw)

    assert item.title == "Hello World"
    assert item.source == "hackernews"
    assert item.summary == ""
    assert item.score == 0.0
    assert item.id == compute_item_id("https://example.com/x")


def test_normalized_item_uses_provided_published_at():
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    raw = RawItem(source="x", title="t", url="https://example.com/y", published_at=ts)
    item = NormalizedItem.from_raw(raw)
    assert item.published_at == ts
