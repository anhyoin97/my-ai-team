import json
from unittest.mock import MagicMock, patch

import httpx

from collector.thumbnail import fetch_thumbnail

_GOOGLE_NEWS_URL = (
    "https://news.google.com/rss/articles/CBMigwFBVV95cUxNUmRfTE84TzhYM09"
    "fcHNUTGJsOHkzV05DU21WM3F4eTBhWEFtcElReXczaUNEOEszZTlUQ0N0eGZwMGI5ckVp"
    "dllyZThZT1RscHQzODVUMGR1SnNxaG94U2RTWDNyRDVkN2t1aFdZMThvY1J3RTFNZUNQR"
    "VlNZThsVkRVVQ?oc=5"
)
_GOOGLE_NEWS_REDIRECT_HTML = """
<html><head></head><body>
<c-wiz><div jscontroller="aLI87" data-n-a-id="ARTICLE_ID"
data-n-a-ts="1787637576" data-n-a-sg="SIGNATURE"></div></c-wiz>
</body></html>
"""


def _batchexecute_response(resolved_url: str) -> str:
    inner = json.dumps(["garturlres", resolved_url, 1])
    payload = [["wrb.fr", "Fbv4je", inner, None, None, None, ""], ["di", 13]]
    return ")]}'\n\n" + json.dumps(payload)


class TestFetchThumbnail:
    def test_returns_og_image_from_meta_tag(self) -> None:
        html = """
        <html><head>
        <meta property="og:image" content="https://example.com/thumb.jpg">
        <meta name="twitter:image" content="https://example.com/other.jpg">
        </head></html>
        """
        with patch("collector.thumbnail._fetch_html", return_value=html):
            result = fetch_thumbnail("https://example.com/article")

        assert result.thumbnail_url == "https://example.com/thumb.jpg"
        assert result.resolved_url == "https://example.com/article"

    def test_falls_back_to_twitter_image_when_og_image_missing(self) -> None:
        html = """
        <html><head>
        <meta name="twitter:image" content="https://example.com/twitter.jpg">
        </head></html>
        """
        with patch("collector.thumbnail._fetch_html", return_value=html):
            result = fetch_thumbnail("https://example.com/article")

        assert result.thumbnail_url == "https://example.com/twitter.jpg"

    def test_handles_content_attribute_before_property_attribute(self) -> None:
        html = """
        <html><head>
        <meta content="https://example.com/reordered.jpg" property="og:image">
        </head></html>
        """
        with patch("collector.thumbnail._fetch_html", return_value=html):
            result = fetch_thumbnail("https://example.com/article")

        assert result.thumbnail_url == "https://example.com/reordered.jpg"

    def test_returns_none_when_no_image_meta_tags_present(self) -> None:
        html = "<html><head><title>No image here</title></head></html>"

        with patch("collector.thumbnail._fetch_html", return_value=html):
            result = fetch_thumbnail("https://example.com/article")

        assert result.thumbnail_url is None
        assert result.resolved_url == "https://example.com/article"

    def test_returns_none_when_request_fails(self) -> None:
        with patch(
            "collector.thumbnail._fetch_html",
            side_effect=httpx.HTTPStatusError("boom", request=None, response=None),  # type: ignore[arg-type]
        ):
            result = fetch_thumbnail("https://example.com/article")

        assert result.thumbnail_url is None

    def test_returns_none_on_timeout(self) -> None:
        with patch(
            "collector.thumbnail._fetch_html", side_effect=httpx.TimeoutException("timed out")
        ):
            result = fetch_thumbnail("https://example.com/article", timeout=1.0)

        assert result.thumbnail_url is None

    def test_fetch_html_requests_with_follow_redirects_enabled(self) -> None:
        """news.google.com 리다이렉트 링크는 follow_redirects 없이는 최종 목적지에
        도달하지 못하므로, httpx 요청 시 follow_redirects=True가 실제로 전달되는지
        확인한다 (리다이렉트 자체를 모킹으로 재현하기는 까다로우므로 설정값만 검증)."""
        from collector.thumbnail import _fetch_html

        mock_response = MagicMock()
        mock_response.iter_text.return_value = ["<html></html>"]
        mock_stream_cm = MagicMock()
        mock_stream_cm.__enter__.return_value = mock_response
        mock_stream_cm.__exit__.return_value = False

        with patch("httpx.stream", return_value=mock_stream_cm) as mock_stream:
            _fetch_html("https://example.com/article", timeout=4.0)

        assert mock_stream.call_args.kwargs["follow_redirects"] is True

    def test_google_news_redirect_is_decoded_before_fetching_thumbnail(self) -> None:
        html = """
        <html><head>
        <meta property="og:image" content="https://chosun.com/thumb.jpg">
        </head></html>
        """
        with (
            patch(
                "collector.thumbnail._fetch_html",
                side_effect=[_GOOGLE_NEWS_REDIRECT_HTML, html],
            ),
            patch("httpx.post") as mock_post,
        ):
            mock_post.return_value = MagicMock(
                text=_batchexecute_response("https://chosun.com/real-article"),
                raise_for_status=MagicMock(),
            )
            result = fetch_thumbnail(_GOOGLE_NEWS_URL)

        assert result.resolved_url == "https://chosun.com/real-article"
        assert result.thumbnail_url == "https://chosun.com/thumb.jpg"

    def test_google_news_redirect_falls_back_to_original_url_on_decode_failure(self) -> None:
        with (
            patch("collector.thumbnail._fetch_html", side_effect=["<html></html>", ""]),
        ):
            result = fetch_thumbnail(_GOOGLE_NEWS_URL)

        assert result.resolved_url == _GOOGLE_NEWS_URL
        assert result.thumbnail_url is None

    def test_non_google_news_url_skips_decoding_step(self) -> None:
        with (
            patch("collector.thumbnail._fetch_html", return_value="<html></html>") as mock_fetch,
            patch("httpx.post") as mock_post,
        ):
            fetch_thumbnail("https://example.com/article")

        mock_post.assert_not_called()
        assert mock_fetch.call_count == 1
