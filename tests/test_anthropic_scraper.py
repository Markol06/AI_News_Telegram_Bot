"""Tests for the Anthropic blog scraper."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest

from src.scrapers.anthropic_scraper import (
    fetch_anthropic_articles,
    fetch_article_content,
    _parse_date,
    _is_article_url,
    _find_date_near,
    SECTIONS,
)


def _make_section_html(articles):
    """Build a fake section page HTML with article links and dates."""
    items = []
    for art in articles:
        items.append(
            f'<div><a href="{art["href"]}">{art["title"]}</a>'
            f'<span>{art["date"]}</span></div>'
        )
    return f"<html><body>{''.join(items)}</body></html>"


def _today_str():
    return datetime.now(timezone.utc).strftime("%b %d, %Y")


def _old_date_str():
    old = datetime.now(timezone.utc) - timedelta(days=30)
    return old.strftime("%b %d, %Y")


class TestFetchAnthropicArticles:
    @patch("src.scrapers.anthropic_scraper.requests.get")
    def test_returns_recent_articles(self, mock_get):
        today = _today_str()
        html = _make_section_html([
            {"href": "/research/article-one", "title": "Research Article One", "date": today},
            {"href": "/research/article-two", "title": "Research Article Two Title", "date": today},
        ])
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        articles = fetch_anthropic_articles(days=7)

        assert len(articles) >= 2
        assert articles[0]["title"] == "Research Article One"
        assert articles[0]["url"] == "https://www.anthropic.com/research/article-one"

    @patch("src.scrapers.anthropic_scraper.requests.get")
    def test_filters_old_articles(self, mock_get):
        old_date = _old_date_str()
        html = _make_section_html([
            {"href": "/research/old-article", "title": "Old Research Article Title", "date": old_date},
        ])
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        articles = fetch_anthropic_articles(days=7)
        assert len(articles) == 0

    @patch("src.scrapers.anthropic_scraper.requests.get")
    def test_deduplicates_across_sections(self, mock_get):
        today = _today_str()
        html = _make_section_html([
            {"href": "/research/shared-article", "title": "Shared Article Title Here", "date": today},
        ])
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        articles = fetch_anthropic_articles(days=7)

        urls = [a["url"] for a in articles]
        assert len(urls) == len(set(urls)), "Duplicate URLs found"

    @patch("src.scrapers.anthropic_scraper.requests.get")
    def test_scrapes_all_four_sections(self, mock_get):
        html = _make_section_html([])
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        fetch_anthropic_articles(days=7)

        assert mock_get.call_count == 4
        called_urls = [call.args[0] for call in mock_get.call_args_list]
        for section in SECTIONS:
            assert section in called_urls

    @patch("src.scrapers.anthropic_scraper.requests.get")
    def test_continues_on_section_failure(self, mock_get):
        today = _today_str()
        good_html = _make_section_html([
            {"href": "/news/good-article", "title": "Good Article Title Here", "date": today},
        ])
        good_response = MagicMock()
        good_response.text = good_html
        good_response.raise_for_status = MagicMock()

        def side_effect(url, **kwargs):
            if "research" in url:
                raise ConnectionError("timeout")
            return good_response

        mock_get.side_effect = side_effect

        articles = fetch_anthropic_articles(days=7)
        # Should still get articles from non-failing sections
        assert len(articles) >= 1

    @patch("src.scrapers.anthropic_scraper.requests.get")
    def test_returns_correct_dict_shape(self, mock_get):
        today = _today_str()
        html = _make_section_html([
            {"href": "/engineering/cool-thing", "title": "Cool Engineering Thing Title", "date": today},
        ])
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        articles = fetch_anthropic_articles(days=7)
        assert len(articles) >= 1

        art = articles[0]
        assert "title" in art
        assert "url" in art
        assert "date" in art
        assert "content" in art


class TestFetchArticleContent:
    @patch("src.scrapers.anthropic_scraper.requests.get")
    def test_extracts_article_text(self, mock_get):
        html = """
        <html>
        <head><style>body{}</style></head>
        <body>
        <nav>Menu</nav>
        <article><p>This is the article content about AI safety.</p></article>
        <footer>Footer</footer>
        </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        content = fetch_article_content("https://www.anthropic.com/research/test")
        assert "article content about AI safety" in content
        assert "Menu" not in content
        assert "Footer" not in content


class TestParseDate:
    def test_parses_standard_date(self):
        result = _parse_date("Mar 5, 2026")
        assert result == datetime(2026, 3, 5, tzinfo=timezone.utc)

    def test_parses_date_without_comma(self):
        result = _parse_date("Mar 5 2026")
        assert result == datetime(2026, 3, 5, tzinfo=timezone.utc)

    def test_returns_none_for_invalid(self):
        assert _parse_date("not a date") is None


class TestIsArticleUrl:
    def test_research_url(self):
        assert _is_article_url(
            "https://www.anthropic.com/research/some-article",
            "https://www.anthropic.com",
        )

    def test_section_index_rejected(self):
        assert not _is_article_url(
            "https://www.anthropic.com/research",
            "https://www.anthropic.com",
        )

    def test_alignment_article(self):
        assert _is_article_url(
            "https://alignment.anthropic.com/some-post",
            "https://alignment.anthropic.com",
        )

    def test_alignment_root_rejected(self):
        assert not _is_article_url(
            "https://alignment.anthropic.com/",
            "https://alignment.anthropic.com",
        )
