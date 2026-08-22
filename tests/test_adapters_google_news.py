from pathlib import Path
from unittest.mock import patch

from collector.adapters.base import SourceAdapter
from collector.adapters.google_news import GoogleNewsAdapter

FIXTURES = Path(__file__).parent / "fixtures" / "google_news"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestGoogleNewsAdapter:
    def test_satisfies_source_adapter_protocol(self) -> None:
        adapter = GoogleNewsAdapter(keyword="인공지능")
        assert isinstance(adapter, SourceAdapter)

    def test_builds_search_url_from_keyword(self) -> None:
        adapter = GoogleNewsAdapter(keyword="인공지능")
        assert adapter.url.startswith("https://news.google.com/rss/search?q=")
        assert "hl=ko&gl=KR&ceid=KR:ko" in adapter.url

    def test_fetch_returns_expected_items_from_sample_response(self) -> None:
        adapter = GoogleNewsAdapter(keyword="인공지능")
        with patch.object(
            adapter, "_fetch_raw_response", return_value=load_fixture("sample_feed.xml")
        ):
            items = adapter.fetch()

        assert len(items) == 3
        assert all(item.source == "google_news" for item in items)
        assert items[0].title == "AI 기술 발전, 산업 전반에 영향 - 조선일보"
        assert items[0].url == "https://news.google.com/rss/articles/CBMiAAAA1?oc=5"
        assert items[0].published_at is not None
        assert items[0].summary

    def test_fetch_returns_empty_list_for_empty_response(self) -> None:
        adapter = GoogleNewsAdapter(keyword="존재하지않는검색어아무결과없음")
        with patch.object(
            adapter, "_fetch_raw_response", return_value=load_fixture("sample_feed_empty.xml")
        ):
            items = adapter.fetch()

        assert items == []

    def test_fetch_skips_entries_missing_title_or_link(self) -> None:
        adapter = GoogleNewsAdapter(keyword="인공지능")
        with patch.object(
            adapter,
            "_fetch_raw_response",
            return_value=load_fixture("sample_feed_partial_broken.xml"),
        ):
            items = adapter.fetch()

        # title 없는 항목, link 없는 항목은 건너뛰고 나머지 2건만 남아야 한다
        assert len(items) == 2
        urls = {item.url for item in items}
        assert "https://news.google.com/rss/articles/CBMiAAAA1?oc=5" in urls
        assert "https://news.google.com/rss/articles/CBMiAAAA4?oc=5" in urls

    def test_fetch_handles_entry_without_published_date(self) -> None:
        adapter = GoogleNewsAdapter(keyword="인공지능")
        with patch.object(
            adapter,
            "_fetch_raw_response",
            return_value=load_fixture("sample_feed_partial_broken.xml"),
        ):
            items = adapter.fetch()

        no_pubdate_item = next(
            item
            for item in items
            if item.url == "https://news.google.com/rss/articles/CBMiAAAA4?oc=5"
        )
        assert no_pubdate_item.published_at is None
