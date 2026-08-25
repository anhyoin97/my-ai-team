from unittest.mock import patch

import httpx

from collector.thumbnail import fetch_thumbnail_url


class TestFetchThumbnailUrl:
    def test_returns_og_image_from_meta_tag(self) -> None:
        html = """
        <html><head>
        <meta property="og:image" content="https://example.com/thumb.jpg">
        <meta name="twitter:image" content="https://example.com/other.jpg">
        </head></html>
        """
        with patch("collector.thumbnail._fetch_html", return_value=html):
            result = fetch_thumbnail_url("https://example.com/article")

        assert result == "https://example.com/thumb.jpg"

    def test_falls_back_to_twitter_image_when_og_image_missing(self) -> None:
        html = """
        <html><head>
        <meta name="twitter:image" content="https://example.com/twitter.jpg">
        </head></html>
        """
        with patch("collector.thumbnail._fetch_html", return_value=html):
            result = fetch_thumbnail_url("https://example.com/article")

        assert result == "https://example.com/twitter.jpg"

    def test_handles_content_attribute_before_property_attribute(self) -> None:
        html = """
        <html><head>
        <meta content="https://example.com/reordered.jpg" property="og:image">
        </head></html>
        """
        with patch("collector.thumbnail._fetch_html", return_value=html):
            result = fetch_thumbnail_url("https://example.com/article")

        assert result == "https://example.com/reordered.jpg"

    def test_returns_none_when_no_image_meta_tags_present(self) -> None:
        html = "<html><head><title>No image here</title></head></html>"

        with patch("collector.thumbnail._fetch_html", return_value=html):
            result = fetch_thumbnail_url("https://example.com/article")

        assert result is None

    def test_returns_none_when_request_fails(self) -> None:
        with patch(
            "collector.thumbnail._fetch_html",
            side_effect=httpx.HTTPStatusError("boom", request=None, response=None),  # type: ignore[arg-type]
        ):
            result = fetch_thumbnail_url("https://example.com/article")

        assert result is None

    def test_returns_none_on_timeout(self) -> None:
        with patch(
            "collector.thumbnail._fetch_html", side_effect=httpx.TimeoutException("timed out")
        ):
            result = fetch_thumbnail_url("https://example.com/article", timeout=1.0)

        assert result is None
