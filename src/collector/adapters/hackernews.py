"""Hacker News 프론트페이지 RSS 어댑터 (https://hnrss.org/frontpage)."""
from __future__ import annotations

from calendar import timegm
from datetime import datetime, timezone

import feedparser
import httpx

from collector.models import RawItem

FRONTPAGE_URL = "https://hnrss.org/frontpage"


class HackerNewsAdapter:
    """Hacker News 프론트페이지 RSS를 가져와 RawItem으로 변환하는 어댑터."""

    name = "hackernews"

    def __init__(self, url: str = FRONTPAGE_URL) -> None:
        self.url = url

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
            title = entry.get("title")
            url = entry.get("link")
            if not title or not url:
                continue
            items.append(
                RawItem(
                    source=self.name,
                    title=title,
                    url=url,
                    published_at=_parse_published(entry),
                    summary=entry.get("summary"),
                )
            )
        return items


def _parse_published(entry: feedparser.FeedParserDict) -> datetime | None:
    parsed_time = entry.get("published_parsed")
    if parsed_time is None:
        return None
    return datetime.fromtimestamp(timegm(parsed_time), tz=timezone.utc)
