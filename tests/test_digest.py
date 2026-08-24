from datetime import datetime, timezone
from pathlib import Path

from collector.digest import render_digest_markdown, write_digest_file
from collector.models import NormalizedItem


def make_item(
    title: str = "title",
    score: float = 1.0,
    published_at: datetime | None = None,
    **kwargs: object,
) -> NormalizedItem:
    defaults: dict[str, object] = {
        "id": "abc123",
        "source": "test-source",
        "title": title,
        "url": "https://example.com/x",
        "published_at": published_at or datetime(2026, 1, 1, tzinfo=timezone.utc),
        "summary": "summary text",
        "score": score,
    }
    defaults.update(kwargs)
    return NormalizedItem(**defaults)  # type: ignore[arg-type]


def test_empty_items_returns_notice_without_error():
    markdown = render_digest_markdown([], generated_at=datetime(2026, 8, 24, tzinfo=timezone.utc))

    assert "이번 주는 새로운 항목이 없습니다." in markdown


def test_sorted_by_score_descending():
    low = make_item(title="low score", score=1.0)
    high = make_item(title="high score", score=5.0)
    mid = make_item(title="mid score", score=3.0)

    markdown = render_digest_markdown([low, high, mid], generated_at=datetime(2026, 8, 24))

    assert markdown.index("high score") < markdown.index("mid score") < markdown.index("low score")


def test_tie_score_sorted_by_published_at_descending():
    older = make_item(
        title="older item", score=2.0, published_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    newer = make_item(
        title="newer item", score=2.0, published_at=datetime(2026, 6, 1, tzinfo=timezone.utc)
    )

    markdown = render_digest_markdown([older, newer], generated_at=datetime(2026, 8, 24))

    assert markdown.index("newer item") < markdown.index("older item")


def test_markdown_includes_title_link_and_source():
    item = make_item(title="My Article", score=1.0)
    item = item.model_copy(update={"url": "https://example.com/article", "source": "hackernews"})

    markdown = render_digest_markdown([item], generated_at=datetime(2026, 8, 24))

    assert "[My Article](https://example.com/article)" in markdown
    assert "hackernews" in markdown


def test_digest_title_and_generated_date_are_rendered():
    markdown = render_digest_markdown(
        [], generated_at=datetime(2026, 8, 24), title="커스텀 제목"
    )

    assert "커스텀 제목" in markdown
    assert "2026-08-24" in markdown


def test_summary_is_truncated_and_included():
    long_summary = "가" * 200
    item = make_item(title="긴 요약 항목", summary=long_summary)

    markdown = render_digest_markdown([item], generated_at=datetime(2026, 8, 24))

    assert long_summary not in markdown
    assert "가" * 120 in markdown


def test_write_digest_file_creates_directory_and_file(tmp_path: Path):
    output_dir = tmp_path / "digests"
    markdown = "# 다이제스트\n\n내용\n"

    path = write_digest_file(
        markdown, output_dir=str(output_dir), generated_at=datetime(2026, 8, 24)
    )

    assert Path(path).exists()
    assert Path(path).name == "2026-08-24-digest.md"


def test_write_digest_file_content_matches(tmp_path: Path):
    markdown = "# 다이제스트\n\n항목 내용\n"

    path = write_digest_file(
        markdown, output_dir=str(tmp_path), generated_at=datetime(2026, 8, 24)
    )

    assert Path(path).read_text(encoding="utf-8") == markdown


def test_write_digest_file_returns_path_inside_output_dir(tmp_path: Path):
    path = write_digest_file(
        "content", output_dir=str(tmp_path), generated_at=datetime(2026, 8, 24)
    )

    assert Path(path).parent == tmp_path
