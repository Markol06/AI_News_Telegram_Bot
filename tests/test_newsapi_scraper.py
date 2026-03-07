"""Tests for NewsAPI scraper (with GNews fallback)."""

from unittest.mock import patch, MagicMock

from src.scrapers.newsapi_scraper import (
    fetch_newsapi_articles,
    _fetch_from_newsapi,
    _fetch_from_gnews,
    fetch_article_content,
    MAX_ARTICLES,
)


def _make_newsapi_response(articles):
    """Build a mock NewsAPI JSON response."""
    return {"status": "ok", "totalResults": len(articles), "articles": articles}


def _make_newsapi_article(i):
    return {
        "title": f"Article {i}",
        "url": f"https://example.com/article-{i}",
        "publishedAt": "2026-03-05T12:00:00Z",
        "description": f"Description for article {i}",
    }


def _make_gnews_article(i):
    return {
        "title": f"GNews Article {i}",
        "url": f"https://gnews.example.com/article-{i}",
        "publishedAt": "2026-03-05T10:00:00Z",
        "description": f"GNews description {i}",
    }


class TestFetchFromNewsAPI:
    @patch.dict("os.environ", {"NEWSAPI_KEY": "test-key"})
    @patch("src.scrapers.newsapi_scraper.requests.get")
    def test_returns_articles_from_newsapi(self, mock_get):
        articles = [_make_newsapi_article(i) for i in range(5)]
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_newsapi_response(articles)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _fetch_from_newsapi(7)

        assert len(result) == 5
        assert result[0]["title"] == "Article 0"
        assert result[0]["url"] == "https://example.com/article-0"
        assert result[0]["date"] == "2026-03-05T12:00:00Z"
        assert result[0]["content"] == "Description for article 0"

    @patch.dict("os.environ", {"NEWSAPI_KEY": "test-key"})
    @patch("src.scrapers.newsapi_scraper.requests.get")
    def test_passes_correct_params(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_newsapi_response([])
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        _fetch_from_newsapi(7)

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["sortBy"] == "popularity"
        assert params["pageSize"] == MAX_ARTICLES
        assert params["apiKey"] == "test-key"
        assert "from" in params

    @patch.dict("os.environ", {}, clear=True)
    def test_returns_empty_when_no_api_key(self):
        result = _fetch_from_newsapi(7)
        assert result == []

    @patch.dict("os.environ", {"NEWSAPI_KEY": "test-key"})
    @patch("src.scrapers.newsapi_scraper.requests.get")
    def test_returns_empty_on_api_error(self, mock_get):
        mock_get.side_effect = Exception("Connection error")
        result = _fetch_from_newsapi(7)
        assert result == []

    @patch.dict("os.environ", {"NEWSAPI_KEY": "test-key"})
    @patch("src.scrapers.newsapi_scraper.requests.get")
    def test_returns_empty_on_bad_status(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "error", "message": "rate limited"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _fetch_from_newsapi(7)
        assert result == []


class TestFetchFromGNews:
    @patch.dict("os.environ", {"GNEWS_API_KEY": "gnews-key"})
    @patch("src.scrapers.newsapi_scraper.requests.get")
    def test_returns_articles_from_gnews(self, mock_get):
        articles = [_make_gnews_article(i) for i in range(3)]
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"totalArticles": 3, "articles": articles}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _fetch_from_gnews(7)

        assert len(result) == 3
        assert result[0]["title"] == "GNews Article 0"
        assert result[0]["url"] == "https://gnews.example.com/article-0"

    @patch.dict("os.environ", {}, clear=True)
    def test_returns_empty_when_no_api_key(self):
        result = _fetch_from_gnews(7)
        assert result == []

    @patch.dict("os.environ", {"GNEWS_API_KEY": "gnews-key"})
    @patch("src.scrapers.newsapi_scraper.requests.get")
    def test_returns_empty_on_error(self, mock_get):
        mock_get.side_effect = Exception("timeout")
        result = _fetch_from_gnews(7)
        assert result == []


class TestFetchNewsapiArticles:
    @patch("src.scrapers.newsapi_scraper._fetch_from_gnews")
    @patch("src.scrapers.newsapi_scraper._fetch_from_newsapi")
    def test_returns_newsapi_results_when_enough(self, mock_newsapi, mock_gnews):
        mock_newsapi.return_value = [
            {"title": f"A{i}", "url": f"https://a.com/{i}", "date": "", "content": ""}
            for i in range(5)
        ]

        result = fetch_newsapi_articles(7)

        assert len(result) == 5
        mock_gnews.assert_not_called()

    @patch("src.scrapers.newsapi_scraper._fetch_from_gnews")
    @patch("src.scrapers.newsapi_scraper._fetch_from_newsapi")
    def test_falls_back_to_gnews_when_insufficient(self, mock_newsapi, mock_gnews):
        mock_newsapi.return_value = [
            {"title": "A1", "url": "https://a.com/1", "date": "", "content": ""}
        ]
        mock_gnews.return_value = [
            {"title": f"G{i}", "url": f"https://g.com/{i}", "date": "", "content": ""}
            for i in range(5)
        ]

        result = fetch_newsapi_articles(7)

        assert len(result) == 5
        assert result[0]["title"] == "A1"
        assert result[1]["title"] == "G0"
        mock_gnews.assert_called_once()

    @patch("src.scrapers.newsapi_scraper._fetch_from_gnews")
    @patch("src.scrapers.newsapi_scraper._fetch_from_newsapi")
    def test_deduplicates_across_sources(self, mock_newsapi, mock_gnews):
        mock_newsapi.return_value = [
            {"title": "A1", "url": "https://shared.com/1", "date": "", "content": ""}
        ]
        mock_gnews.return_value = [
            {"title": "G1", "url": "https://shared.com/1", "date": "", "content": ""},
            {"title": "G2", "url": "https://g.com/2", "date": "", "content": ""},
        ]

        result = fetch_newsapi_articles(7)

        urls = [a["url"] for a in result]
        assert urls.count("https://shared.com/1") == 1

    @patch("src.scrapers.newsapi_scraper._fetch_from_gnews")
    @patch("src.scrapers.newsapi_scraper._fetch_from_newsapi")
    def test_caps_at_max_articles(self, mock_newsapi, mock_gnews):
        mock_newsapi.return_value = [
            {"title": f"A{i}", "url": f"https://a.com/{i}", "date": "", "content": ""}
            for i in range(3)
        ]
        mock_gnews.return_value = [
            {"title": f"G{i}", "url": f"https://g.com/{i}", "date": "", "content": ""}
            for i in range(10)
        ]

        result = fetch_newsapi_articles(7)
        assert len(result) == MAX_ARTICLES


class TestFetchArticleContent:
    @patch("src.scrapers.newsapi_scraper.requests.get")
    def test_extracts_article_text(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = "<html><body><article><p>Hello world</p></article></body></html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = fetch_article_content("https://example.com/article")
        assert "Hello world" in result

    @patch("src.scrapers.newsapi_scraper.requests.get")
    def test_returns_empty_on_error(self, mock_get):
        mock_get.side_effect = Exception("404")
        result = fetch_article_content("https://example.com/missing")
        assert result == ""
