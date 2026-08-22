"""Google News 키워드 검색 어댑터."""
from __future__ import annotations

from datetime import datetime, timezone
from time import struct_time
from urllib.parse import quote

import feedparser
import httpx

from collector.models import RawItem

_FEED_URL_TEMPLATE = "https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"


class GoogleNewsAdapter:
    """키워드로 Google News RSS를 검색해 RawItem 리스트로 반환하는 어댑터."""

    name = "google_news"

    def __init__(self, keyword: str) -> None:
        self.keyword = keyword
        self.url = _FEED_URL_TEMPLATE.format(keyword=quote(keyword))

    def _fetch_raw_response(self) -> str:
        """실제 네트워크 호출. 테스트에서는 이 메서드만 mock한다."""
        response = httpx.get(self.url, timeout=10)
        response.raise_for_status()
        return response.text

    def fetch(self) -> list[RawItem]:
        text = self._fetch_raw_response()
        return self._parse(text)

    def _parse(self, text: str) -> list[RawItem]:
        parsed = feedparser.parse(text)
        items: list[RawItem] = []
        for entry in parsed.entries:
            title: str | None = entry.get("title")
            link: str | None = entry.get("link")
            if not title or not link:
                continue
            items.append(
                RawItem(
                    source=self.name,
                    title=title,
                    url=link,
                    published_at=_parse_published(entry.get("published_parsed")),
                    summary=entry.get("summary"),
                )
            )
        return items


def _parse_published(published_parsed: struct_time | None) -> datetime | None:
    if published_parsed is None:
        return None
    return datetime(*published_parsed[:6], tzinfo=timezone.utc)
