from datetime import datetime, timezone

from collector.models import NormalizedItem
from collector.scoring import score_items


def make_item(title: str = "title", summary: str = "summary", **kwargs: object) -> NormalizedItem:
    defaults: dict[str, object] = {
        "id": "abc123",
        "source": "test",
        "title": title,
        "url": "https://example.com/x",
        "published_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "summary": summary,
    }
    defaults.update(kwargs)
    return NormalizedItem(**defaults)  # type: ignore[arg-type]


def test_no_keyword_match_is_excluded():
    item = make_item(title="hello world", summary="nothing special")
    result = score_items([item], keywords=["python", "rust"])

    assert result == []


def test_keyword_matched_in_title():
    item = make_item(title="Python 3.13 released", summary="general summary")
    result = score_items([item], keywords=["python"])

    assert len(result) == 1
    assert result[0].keywords_matched == ["python"]
    assert result[0].score == 1.0


def test_keyword_matched_in_summary():
    item = make_item(title="release notes", summary="written in Rust for speed")
    result = score_items([item], keywords=["rust"])

    assert len(result) == 1
    assert result[0].keywords_matched == ["rust"]
    assert result[0].score == 1.0


def test_matching_is_case_insensitive():
    item = make_item(title="PYTHON tips", summary="")
    result = score_items([item], keywords=["python"])

    assert len(result) == 1
    assert result[0].keywords_matched == ["python"]


def test_multiple_keyword_matches_accumulate_score():
    item = make_item(title="Python and Rust news", summary="also mentions Go")
    result = score_items([item], keywords=["python", "rust", "go", "java"])

    assert len(result) == 1
    assert result[0].keywords_matched == ["python", "rust", "go"]
    assert result[0].score == 3.0


def test_threshold_boundary_is_inclusive():
    item = make_item(title="Python news", summary="")
    below = score_items([item], keywords=["python"], threshold=1.0)
    above = score_items([item], keywords=["python"], threshold=1.5)

    assert len(below) == 1
    assert above == []


def test_original_item_is_not_mutated():
    item = make_item(title="Python news", summary="")
    score_items([item], keywords=["python"])

    assert item.keywords_matched == []
    assert item.score == 0.0


def test_returns_new_instance_not_same_object():
    item = make_item(title="Python news", summary="")
    result = score_items([item], keywords=["python"])

    assert result[0] is not item
    assert result[0].id == item.id
