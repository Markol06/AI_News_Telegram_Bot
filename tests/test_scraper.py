"""Tests for the scraper module."""

import json
from unittest.mock import patch, Mock

import pytest
import requests

from src.scrapers.batch_scraper import (
    fetch_articles,
    fetch_article_content,
    _parse_from_next_data,
    _parse_from_html,
    _extract_content_from_next_data,
    _html_to_text,
)


SAMPLE_NEXT_DATA = {
    "props": {
        "pageProps": {
            "posts": [
                {
                    "title": "Gemini Seizes the Lead",
                    "slug": "issue-342",
                    "published_at": "2026-02-27T06:59:06.000-08:00",
                },
                {
                    "title": "The New Open-Weights Leader",
                    "slug": "issue-341",
                    "published_at": "2026-02-20T06:59:06.000-08:00",
                },
                {
                    "title": "Claude Opus 4.6 Thinks Smarter",
                    "slug": "issue-340",
                    "published_at": "2026-02-13T06:59:06.000-08:00",
                },
            ]
        }
    }
}


def _build_next_data_html(data):
    return f"""
    <html><head>
    <script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>
    </head><body></body></html>
    """


def _build_fallback_html():
    return """
    <html><body>
    <a href="/the-batch/issue-342/">Gemini Seizes the Lead</a>
    <a href="/the-batch/issue-341/">The New Open-Weights Leader</a>
    <a href="/the-batch/issue-340/">Claude Opus 4.6 Thinks Smarter</a>
    </body></html>
    """


class TestParseFromNextData:
    def test_parses_articles(self):
        html = _build_next_data_html(SAMPLE_NEXT_DATA)
        articles = _parse_from_next_data(html)

        assert len(articles) == 3
        assert articles[0]["title"] == "Gemini Seizes the Lead"
        assert articles[0]["url"] == "https://www.deeplearning.ai/the-batch/issue-342/"
        assert articles[0]["date"] == "2026-02-27T06:59:06.000-08:00"

    def test_returns_empty_when_no_script(self):
        html = "<html><body>No data here</body></html>"
        assert _parse_from_next_data(html) == []

    def test_returns_empty_when_no_posts(self):
        data = {"props": {"pageProps": {}}}
        html = _build_next_data_html(data)
        assert _parse_from_next_data(html) == []

    def test_skips_entries_without_title(self):
        data = {"props": {"pageProps": {"posts": [
            {"title": "", "slug": "issue-1", "published_at": ""},
            {"title": "Valid", "slug": "issue-2", "published_at": "2026-01-01"},
        ]}}}
        html = _build_next_data_html(data)
        articles = _parse_from_next_data(html)
        assert len(articles) == 1
        assert articles[0]["title"] == "Valid"


class TestParseFromHtml:
    def test_parses_links(self):
        html = _build_fallback_html()
        articles = _parse_from_html(html)

        assert len(articles) == 3
        assert articles[0]["title"] == "Gemini Seizes the Lead"
        assert articles[0]["url"] == "https://www.deeplearning.ai/the-batch/issue-342/"

    def test_deduplicates_links(self):
        html = """
        <html><body>
        <a href="/the-batch/issue-342/">Title A</a>
        <a href="/the-batch/issue-342/">Title A duplicate</a>
        </body></html>
        """
        articles = _parse_from_html(html)
        assert len(articles) == 1


class TestFetchArticles:
    @patch("src.scrapers.batch_scraper.requests.get")
    def test_uses_next_data(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.text = _build_next_data_html(SAMPLE_NEXT_DATA)
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        articles = fetch_articles(limit=2)

        assert len(articles) == 2
        assert articles[0]["title"] == "Gemini Seizes the Lead"
        mock_get.assert_called_once()

    @patch("src.scrapers.batch_scraper.requests.get")
    def test_falls_back_to_html(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.text = _build_fallback_html()
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        articles = fetch_articles(limit=10)

        assert len(articles) == 3
        assert articles[0]["url"].startswith("https://")

    @patch("src.scrapers.batch_scraper.requests.get")
    def test_network_error_raises(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("fail")

        with pytest.raises(requests.exceptions.ConnectionError):
            fetch_articles()

    @patch("src.scrapers.batch_scraper.requests.get")
    def test_http_error_raises(self, mock_get):
        mock_resp = Mock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
        mock_get.return_value = mock_resp

        with pytest.raises(requests.exceptions.HTTPError):
            fetch_articles()


SAMPLE_ARTICLE_HTML = "<h1>Gemini Takes the Lead</h1><p>Google updated Gemini.</p><hr><h1>AI Summit</h1><p>The fourth global AI summit showed optimism.</p>"

SAMPLE_ARTICLE_NEXT_DATA = {
    "props": {
        "pageProps": {
            "post": {
                "html": SAMPLE_ARTICLE_HTML,
            }
        }
    }
}


def _build_article_page(data):
    return f"""
    <html><head>
    <script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script>
    </head><body></body></html>
    """


class TestFetchArticleContent:
    @patch("src.scrapers.batch_scraper.requests.get")
    def test_extracts_content_from_next_data(self, mock_get):
        mock_resp = Mock()
        mock_resp.text = _build_article_page(SAMPLE_ARTICLE_NEXT_DATA)
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        content = fetch_article_content("https://www.deeplearning.ai/the-batch/issue-342/")

        assert "Gemini Takes the Lead" in content
        assert "AI Summit" in content
        assert "Google updated Gemini" in content
        assert "<h1>" not in content  # HTML stripped

    @patch("src.scrapers.batch_scraper.requests.get")
    def test_fallback_to_body(self, mock_get):
        html = "<html><body><article><h2>Topic</h2><p>Some content here.</p></article></body></html>"
        mock_resp = Mock()
        mock_resp.text = html
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        content = fetch_article_content("https://example.com/article")

        assert "Topic" in content
        assert "Some content here" in content

    @patch("src.scrapers.batch_scraper.requests.get")
    def test_network_error_raises(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("fail")

        with pytest.raises(requests.exceptions.ConnectionError):
            fetch_article_content("https://example.com/article")


class TestHtmlToText:
    def test_strips_tags(self):
        text = _html_to_text("<p>Hello <b>world</b></p>")
        assert text == "Hello world"

    def test_preserves_section_separators(self):
        text = _html_to_text("<p>Section 1</p><hr><p>Section 2</p>")
        assert "---" in text
        assert "Section 1" in text
        assert "Section 2" in text

    def test_removes_scripts_and_styles(self):
        text = _html_to_text("<p>Text</p><script>alert('x')</script><style>.a{}</style>")
        assert "alert" not in text
        assert ".a{}" not in text
        assert "Text" in text

    def test_handles_headings(self):
        text = _html_to_text("<h1>Title</h1><p>Body</p>")
        assert "Title" in text
        assert "Body" in text
