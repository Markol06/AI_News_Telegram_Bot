"""Tests for The Neuron Daily scraper module."""

from unittest.mock import patch, Mock
from datetime import datetime, timedelta, timezone

import pytest
import requests

from src.scrapers import neuron_scraper
from src.scrapers.neuron_scraper import (
    fetch_neuron_articles,
    fetch_article_content,
    _html_to_text,
    _parse_rfc2822,
    _content_cache,
)


def _build_rss_xml(items_xml):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"
         xmlns:atom="http://www.w3.org/2005/Atom"
         xmlns:content="http://purl.org/rss/1.0/modules/content/">
    <channel>
        <title>The Neuron</title>
        {items_xml}
    </channel>
    </rss>"""


def _recent_rfc2822(days_ago=0):
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


SAMPLE_RSS_WITH_CONTENT = _build_rss_xml(f"""
    <item>
        <title>Google built real-life Pied Piper</title>
        <link>https://www.theneurondaily.com/p/google-built-real-life-pied-piper</link>
        <pubDate>{_recent_rfc2822(1)}</pubDate>
        <dc:creator>Grant Harvey</dc:creator>
        <content:encoded><![CDATA[<h1>Google Pied Piper</h1><p>Google announced compression.</p>]]></content:encoded>
    </item>
    <item>
        <title>AI Summit Highlights</title>
        <link>https://www.theneurondaily.com/p/ai-summit-highlights</link>
        <pubDate>{_recent_rfc2822(3)}</pubDate>
        <dc:creator>Grant Harvey</dc:creator>
        <content:encoded><![CDATA[<h1>AI Summit</h1><p>Key takeaways from the summit.</p>]]></content:encoded>
    </item>
    <item>
        <title>Old Article</title>
        <link>https://www.theneurondaily.com/p/old-article</link>
        <pubDate>{_recent_rfc2822(14)}</pubDate>
        <dc:creator>Grant Harvey</dc:creator>
        <content:encoded><![CDATA[<p>Old content.</p>]]></content:encoded>
    </item>
""")

SAMPLE_RSS_NO_CONTENT = _build_rss_xml(f"""
    <item>
        <title>Google built real-life Pied Piper</title>
        <link>https://www.theneurondaily.com/p/google-built-real-life-pied-piper</link>
        <pubDate>{_recent_rfc2822(1)}</pubDate>
        <dc:creator>Grant Harvey</dc:creator>
    </item>
""")


class TestFetchNeuronArticles:
    def setup_method(self):
        _content_cache.clear()

    @patch("src.scrapers.neuron_scraper.requests.get")
    def test_fetches_recent_articles(self, mock_get):
        mock_resp = Mock()
        mock_resp.text = SAMPLE_RSS_WITH_CONTENT
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        articles = fetch_neuron_articles(days=7)

        assert len(articles) == 2
        assert articles[0]["title"] == "Google built real-life Pied Piper"
        assert articles[0]["url"] == "https://www.theneurondaily.com/p/google-built-real-life-pied-piper"
        assert articles[1]["title"] == "AI Summit Highlights"

    @patch("src.scrapers.neuron_scraper.requests.get")
    def test_caches_content_from_rss(self, mock_get):
        mock_resp = Mock()
        mock_resp.text = SAMPLE_RSS_WITH_CONTENT
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        fetch_neuron_articles(days=7)

        url = "https://www.theneurondaily.com/p/google-built-real-life-pied-piper"
        assert url in _content_cache
        assert "Google" in _content_cache[url]

    @patch("src.scrapers.neuron_scraper.requests.get")
    def test_filters_old_articles(self, mock_get):
        mock_resp = Mock()
        mock_resp.text = SAMPLE_RSS_WITH_CONTENT
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        articles = fetch_neuron_articles(days=2)

        assert len(articles) == 1
        assert articles[0]["title"] == "Google built real-life Pied Piper"

    @patch("src.scrapers.neuron_scraper.requests.get")
    def test_returns_all_with_large_window(self, mock_get):
        mock_resp = Mock()
        mock_resp.text = SAMPLE_RSS_WITH_CONTENT
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        articles = fetch_neuron_articles(days=30)

        assert len(articles) == 3

    @patch("src.scrapers.neuron_scraper.requests.get")
    def test_handles_empty_feed(self, mock_get):
        mock_resp = Mock()
        mock_resp.text = _build_rss_xml("")
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        articles = fetch_neuron_articles()

        assert articles == []

    @patch("src.scrapers.neuron_scraper.requests.get")
    def test_skips_items_without_title(self, mock_get):
        rss = _build_rss_xml(f"""
            <item>
                <link>https://example.com/no-title</link>
                <pubDate>{_recent_rfc2822(1)}</pubDate>
            </item>
            <item>
                <title>Has Title</title>
                <link>https://example.com/has-title</link>
                <pubDate>{_recent_rfc2822(1)}</pubDate>
            </item>
        """)
        mock_resp = Mock()
        mock_resp.text = rss
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        articles = fetch_neuron_articles()

        assert len(articles) == 1
        assert articles[0]["title"] == "Has Title"

    @patch("src.scrapers.neuron_scraper.requests.get")
    def test_network_error_raises(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("fail")

        with pytest.raises(requests.exceptions.ConnectionError):
            fetch_neuron_articles()

    @patch("src.scrapers.neuron_scraper.requests.get")
    def test_http_error_raises(self, mock_get):
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
        mock_get.return_value = mock_resp

        with pytest.raises(requests.exceptions.HTTPError):
            fetch_neuron_articles()


class TestFetchArticleContent:
    def setup_method(self):
        _content_cache.clear()

    def test_returns_cached_content(self):
        url = "https://www.theneurondaily.com/p/cached-article"
        _content_cache[url] = "Cached article text"

        content = fetch_article_content(url)

        assert content == "Cached article text"
        assert url not in _content_cache  # consumed from cache

    @patch("src.scrapers.neuron_scraper.requests.get")
    def test_fetches_from_web_when_not_cached(self, mock_get):
        html = """<html><body>
        <nav>Menu</nav>
        <article><h1>Big AI News</h1><p>Details about the news.</p></article>
        <footer>Copyright</footer>
        </body></html>"""
        mock_resp = Mock()
        mock_resp.text = html
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        content = fetch_article_content("https://www.theneurondaily.com/p/test")

        assert "Big AI News" in content
        assert "Details about the news" in content
        assert "Menu" not in content
        assert "Copyright" not in content

    @patch("src.scrapers.neuron_scraper.requests.get")
    def test_fallback_to_body(self, mock_get):
        html = "<html><body><p>Some content here.</p></body></html>"
        mock_resp = Mock()
        mock_resp.text = html
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        content = fetch_article_content("https://example.com/article")

        assert "Some content here" in content

    @patch("src.scrapers.neuron_scraper.requests.get")
    def test_sends_user_agent_header(self, mock_get):
        html = "<html><body><p>Content</p></body></html>"
        mock_resp = Mock()
        mock_resp.text = html
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        fetch_article_content("https://example.com/article")

        call_kwargs = mock_get.call_args
        assert "User-Agent" in call_kwargs.kwargs.get("headers", {})

    @patch("src.scrapers.neuron_scraper.requests.get")
    def test_network_error_raises(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("fail")

        with pytest.raises(requests.exceptions.ConnectionError):
            fetch_article_content("https://example.com/article")

    @patch("src.scrapers.neuron_scraper.requests.get")
    def test_end_to_end_rss_then_content(self, mock_get):
        """fetch_neuron_articles caches content, fetch_article_content returns it."""
        mock_resp = Mock()
        mock_resp.text = SAMPLE_RSS_WITH_CONTENT
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        articles = fetch_neuron_articles(days=7)
        content = fetch_article_content(articles[0]["url"])

        assert "Google" in content
        # Only one HTTP call (the RSS fetch), no second call for article page
        mock_get.assert_called_once()


class TestHtmlToText:
    def test_strips_tags(self):
        assert _html_to_text("<p>Hello <b>world</b></p>") == "Hello world"

    def test_preserves_section_separators(self):
        text = _html_to_text("<p>Section 1</p><hr><p>Section 2</p>")
        assert "---" in text
        assert "Section 1" in text
        assert "Section 2" in text

    def test_removes_scripts_and_styles(self):
        text = _html_to_text("<p>Text</p><script>alert('x')</script><style>.a{}</style>")
        assert "alert" not in text
        assert "Text" in text

    def test_handles_headings(self):
        text = _html_to_text("<h1>Title</h1><p>Body</p>")
        assert "Title" in text
        assert "Body" in text


class TestParseRfc2822:
    def test_parses_valid_date(self):
        dt = _parse_rfc2822("Fri, 27 Mar 2026 08:35:00 +0000")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 3
        assert dt.day == 27

    def test_returns_none_for_invalid(self):
        assert _parse_rfc2822("not a date") is None

    def test_returns_none_for_empty(self):
        assert _parse_rfc2822("") is None
