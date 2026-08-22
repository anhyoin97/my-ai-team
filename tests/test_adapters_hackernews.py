from pathlib import Path
from unittest.mock import patch

from collector.adapters.base import SourceAdapter
from collector.adapters.hackernews import HackerNewsAdapter

FIXTURES = Path(__file__).parent / "fixtures" / "hackernews"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestHackerNewsAdapter:
    def test_satisfies_source_adapter_protocol(self) -> None:
        adapter = HackerNewsAdapter()
        assert isinstance(adapter, SourceAdapter)

    def test_fetch_returns_expected_items_from_sample_response(self) -> None:
        adapter = HackerNewsAdapter()
        with patch.object(
            adapter, "_fetch_raw_response", return_value=load_fixture("sample_feed.xml")
        ):
            items = adapter.fetch()

        assert len(items) == 3
        first = items[0]
        assert first.source == "hackernews"
        assert first.title == "English ↔ Claudish Translator"
        assert first.url == "https://programasweights.com/claudish"
        assert first.published_at is not None
        assert first.published_at.year == 2026
        assert first.summary

    def test_fetch_returns_empty_list_for_empty_response(self) -> None:
        adapter = HackerNewsAdapter()
        with patch.object(
            adapter, "_fetch_raw_response", return_value=load_fixture("empty_feed.xml")
        ):
            items = adapter.fetch()

        assert items == []

    def test_fetch_skips_malformed_entries_without_crashing(self) -> None:
        adapter = HackerNewsAdapter()
        with patch.object(
            adapter,
            "_fetch_raw_response",
            return_value=load_fixture("sample_feed_partial_broken.xml"),
        ):
            items = adapter.fetch()

        # 제목/링크가 없는 항목 하나는 건너뛰고, 나머지 2개는 정상 반환되어야 한다
        assert len(items) == 2
        assert all(item.title and item.url for item in items)
