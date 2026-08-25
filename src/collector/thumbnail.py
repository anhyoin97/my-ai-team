"""기사 URL에서 뉴스카드용 썸네일 이미지(og:image/twitter:image)를 추출한다.

Google News RSS(`news.google.com/rss/articles/...`)가 내려주는 링크는 실제
언론사 주소가 아니라 Google의 중간 리다이렉트 페이지다. 이 페이지는 일반적인
HTTP 302가 아니라 클라이언트 사이드 스크립트로 실제 URL을 넘겨주기 때문에
`follow_redirects=True`로도 실제 기사 페이지에 도달하지 못한다. 실제 URL은
페이지에 심어진 서명값(`data-n-a-id`/`data-n-a-sg`/`data-n-a-ts`)을 Google의
내부 batchexecute 엔드포인트에 넘겨 디코딩해야 얻을 수 있다.
"""
from __future__ import annotations

import json
from html.parser import HTMLParser
from typing import NamedTuple
from urllib.parse import quote, urlparse

import httpx

_MAX_BYTES = 200_000
# Google News 리다이렉트 페이지는 og:image 스크래핑 대상 페이지보다 훨씬 크고(~600KB),
# 디코딩에 필요한 서명값(data-n-a-id/sg/ts)이 페이지 후반부에 있어 _MAX_BYTES로는
# 잘려나간다. 이 페이지는 매번 다른 임의의 크기가 아니라 Google이 내려주는 고정된
# 구조이므로 더 큰 상한을 둔다.
_GOOGLE_NEWS_REDIRECT_MAX_BYTES = 2_000_000
_GOOGLE_NEWS_HOST = "news.google.com"
_GOOGLE_NEWS_PATH_PREFIX = "/rss/articles/"
_GOOGLE_NEWS_DECODE_URL = "https://news.google.com/_/DotsSplashUi/data/batchexecute"


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


class _GoogleNewsRedirectParser(HTMLParser):
    """Google News 리다이렉트 페이지에서 URL 디코딩에 필요한 서명값을 찾는다."""

    def __init__(self) -> None:
        super().__init__()
        self.article_id: str | None = None
        self.signature: str | None = None
        self.timestamp: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.article_id is not None:
            return
        attr_map = dict(attrs)
        article_id = attr_map.get("data-n-a-id")
        if not article_id:
            return
        self.article_id = article_id
        self.signature = attr_map.get("data-n-a-sg")
        self.timestamp = attr_map.get("data-n-a-ts")


class ThumbnailLookup(NamedTuple):
    """썸네일 조회 결과.

    resolved_url은 Google News 리다이렉트 링크를 디코딩한 실제 언론사 URL이다.
    디코딩 대상이 아니거나 디코딩에 실패하면 입력받은 url을 그대로 담는다.
    """

    thumbnail_url: str | None
    resolved_url: str


def _fetch_html(url: str, timeout: float, max_bytes: int = _MAX_BYTES) -> str:
    """실제 네트워크 요청. 테스트에서는 이 함수만 mock한다.

    본문은 최대 max_bytes까지만 스트리밍으로 읽는다.
    리다이렉트를 따라가야 실제 기사/리다이렉트 페이지에 도달하므로
    follow_redirects=True로 요청한다.
    """
    chunks: list[str] = []
    total_bytes = 0
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as response:
        response.raise_for_status()
        for chunk in response.iter_text():
            chunks.append(chunk)
            total_bytes += len(chunk.encode("utf-8"))
            if total_bytes >= max_bytes:
                break
    return "".join(chunks)


def _is_google_news_redirect(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc == _GOOGLE_NEWS_HOST and parsed.path.startswith(
        _GOOGLE_NEWS_PATH_PREFIX
    )


def _build_decode_request_body(article_id: str, timestamp: str, signature: str) -> str:
    inner_payload = (
        '["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,'
        "null,null,null,null,0,1],"
        f'"X","X",1,[1,1,1],1,1,null,0,0,null,0],"{article_id}",'
        f'{timestamp},"{signature}"]'
    )
    return json.dumps([[["Fbv4je", inner_payload]]])


def _decode_google_news_url(url: str, timeout: float) -> str | None:
    """Google News 리다이렉트 링크를 실제 언론사 URL로 디코딩한다.

    필요한 서명값을 못 찾거나 응답 형식이 예상과 다르면 None을 반환한다
    (호출부에서 원래 url로 폴백하기 위함). 네트워크 예외는 호출부에서 처리한다.
    """
    html = _fetch_html(url, timeout, max_bytes=_GOOGLE_NEWS_REDIRECT_MAX_BYTES)
    parser = _GoogleNewsRedirectParser()
    parser.feed(html)
    if not (parser.article_id and parser.signature and parser.timestamp):
        return None

    request_body = _build_decode_request_body(
        parser.article_id, parser.timestamp, parser.signature
    )
    response = httpx.post(
        _GOOGLE_NEWS_DECODE_URL,
        headers={"content-type": "application/x-www-form-urlencoded;charset=UTF-8"},
        content=f"f.req={quote(request_body)}",
        timeout=timeout,
    )
    response.raise_for_status()
    try:
        payload = json.loads(response.text.split("\n\n")[1])
        decoded_url = json.loads(payload[0][2])[1]
    except (IndexError, ValueError, TypeError):
        return None
    return decoded_url if isinstance(decoded_url, str) else None


def _resolve_url(url: str, timeout: float) -> str:
    """Google News 리다이렉트 링크면 실제 언론사 URL로, 아니면 그대로 반환한다."""
    if not _is_google_news_redirect(url):
        return url
    try:
        decoded = _decode_google_news_url(url, timeout)
    except Exception:
        return url
    return decoded or url


def fetch_thumbnail(url: str, timeout: float = 4.0) -> ThumbnailLookup:
    """url의 og:image(없으면 twitter:image)와 실제 리졸브된 url을 함께 반환한다.

    url이 Google News 리다이렉트 링크면 먼저 실제 언론사 URL로 디코딩한 뒤
    그 페이지에서 썸네일을 찾는다. 요청 실패/타임아웃/파싱 실패 등 어떤 이유로든
    실패해도 예외 없이 처리한다 (다이제스트 생성 자체가 실패해서는 안 되기 때문).
    """
    resolved_url = _resolve_url(url, timeout)
    try:
        html = _fetch_html(resolved_url, timeout)
        parser = _MetaImageParser()
        parser.feed(html)
        thumbnail_url = parser.image_url
    except Exception:
        thumbnail_url = None
    return ThumbnailLookup(thumbnail_url=thumbnail_url, resolved_url=resolved_url)
