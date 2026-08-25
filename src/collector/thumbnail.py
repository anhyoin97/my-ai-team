"""기사 URL에서 뉴스카드용 썸네일 이미지(og:image/twitter:image)를 추출한다."""
from __future__ import annotations

from html.parser import HTMLParser

import httpx

_MAX_BYTES = 200_000


class _MetaImageParser(HTMLParser):
    """og:image / twitter:image meta 태그를 찾는다.

    content 속성이 property/name보다 먼저 오는 경우에도 안전하도록
    태그의 속성을 모두 모은 뒤 판정한다.
    """

    def __init__(self) -> None:
        super().__init__()
        self.og_image: str | None = None
        self.twitter_image: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        attr_map = {key.lower(): value for key, value in attrs if value}
        content = attr_map.get("content")
        if not content:
            return
        identifier = (attr_map.get("property") or attr_map.get("name") or "").lower()
        if identifier == "og:image" and self.og_image is None:
            self.og_image = content
        elif identifier == "twitter:image" and self.twitter_image is None:
            self.twitter_image = content

    @property
    def image_url(self) -> str | None:
        return self.og_image or self.twitter_image


def _fetch_html(url: str, timeout: float) -> str:
    """실제 네트워크 요청. 테스트에서는 이 함수만 mock한다.

    본문은 최대 _MAX_BYTES까지만 스트리밍으로 읽는다.
    """
    chunks: list[str] = []
    total_bytes = 0
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as response:
        response.raise_for_status()
        for chunk in response.iter_text():
            chunks.append(chunk)
            total_bytes += len(chunk.encode("utf-8"))
            if total_bytes >= _MAX_BYTES:
                break
    return "".join(chunks)


def fetch_thumbnail_url(url: str, timeout: float = 4.0) -> str | None:
    """기사 url의 og:image(없으면 twitter:image) 값을 반환한다.

    요청 실패/타임아웃/파싱 실패 등 어떤 이유로든 실패하면 예외 없이
    None을 반환한다 (다이제스트 생성 자체가 실패해서는 안 되기 때문).
    """
    try:
        html = _fetch_html(url, timeout)
        parser = _MetaImageParser()
        parser.feed(html)
        return parser.image_url
    except Exception:
        return None
