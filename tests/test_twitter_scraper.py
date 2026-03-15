"""Tests for Twitter scraper (via RapidAPI)."""

from unittest.mock import patch, MagicMock

from src.scrapers.twitter_scraper import (
    fetch_twitter_articles,
    _search_tweets,
    fetch_article_content,
    MAX_TWEETS,
)


def _make_tweet_entry(i, screen_name="testuser", favorites=100, retweets=50, replies=10):
    return {
        "tweet_id": f"tweet_{i}",
        "text": f"Tweet text number {i} about AI and machine learning",
        "screen_name": screen_name,
        "favorites": favorites,
        "retweets": retweets,
        "replies": replies,
    }


def _make_search_response(entries):
    return {"timeline": entries}


class TestSearchTweets:
    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"})
    @patch("src.scrapers.twitter_scraper.requests.get")
    def test_returns_tweets_from_search(self, mock_get):
        entries = [_make_tweet_entry(i) for i in range(3)]
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_search_response(entries)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _search_tweets("test-key", "AI")

        assert len(result) == 3
        assert "Tweet text number 0" in result[0]["title"]
        assert "x.com" in result[0]["url"]
        assert result[0]["score"] == 100 + 50 * 2 + 10  # favorites + retweets*2 + replies

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"})
    @patch("src.scrapers.twitter_scraper.requests.get")
    def test_sends_rapidapi_headers(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_search_response([])
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        _search_tweets("test-key", "AI")

        call_kwargs = mock_get.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert "x-rapidapi-key" in headers
        assert "x-rapidapi-host" in headers

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"})
    @patch("src.scrapers.twitter_scraper.requests.get")
    def test_returns_empty_on_error(self, mock_get):
        mock_get.side_effect = Exception("Connection error")
        result = _search_tweets("test-key", "AI")
        assert result == []

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"})
    @patch("src.scrapers.twitter_scraper.requests.get")
    def test_skips_entries_without_tweet_id(self, mock_get):
        entries = [{"text": "No ID tweet", "screen_name": "user"}]
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_search_response(entries)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _search_tweets("test-key", "AI")
        assert result == []


class TestFetchTwitterArticles:
    @patch("src.scrapers.twitter_scraper._search_tweets")
    def test_returns_empty_when_no_api_key(self, mock_search):
        with patch.dict("os.environ", {}, clear=True):
            result = fetch_twitter_articles()
        assert result == []
        mock_search.assert_not_called()

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"})
    @patch("src.scrapers.twitter_scraper._search_tweets")
    def test_deduplicates_tweets_by_url(self, mock_search):
        tweet = {
            "title": "@user: Same tweet",
            "url": "https://x.com/user/status/123",
            "score": 500,
            "content": "Same tweet",
        }
        mock_search.return_value = [tweet]

        result = fetch_twitter_articles()

        # Should have only 1 unique tweet despite multiple search calls
        urls = [t["url"] for t in result]
        assert urls.count("https://x.com/user/status/123") == 1

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"})
    @patch("src.scrapers.twitter_scraper._search_tweets")
    def test_sorts_by_score_descending(self, mock_search):
        def side_effect(api_key, query):
            if "artificial" in query:
                return [
                    {"title": "T1", "url": "https://x.com/a/status/1", "score": 100, "content": ""},
                    {"title": "T2", "url": "https://x.com/a/status/2", "score": 500, "content": ""},
                ]
            return []

        mock_search.side_effect = side_effect
        result = fetch_twitter_articles()

        if len(result) >= 2:
            scores = [t["score"] for t in result]
            assert scores == sorted(scores, reverse=True)

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"})
    @patch("src.scrapers.twitter_scraper._search_tweets")
    def test_caps_at_max_tweets(self, mock_search):
        tweets = [
            {"title": f"T{i}", "url": f"https://x.com/u/status/{i}", "score": 100 - i, "content": ""}
            for i in range(20)
        ]
        mock_search.return_value = tweets

        result = fetch_twitter_articles()
        assert len(result) <= MAX_TWEETS


class TestFetchArticleContent:
    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"})
    @patch("src.scrapers.twitter_scraper.requests.get")
    def test_fetches_tweet_detail(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "text": "Full tweet text about AI",
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = fetch_article_content("https://x.com/user/status/12345")
        assert "Full tweet text about AI" in result

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"})
    @patch("src.scrapers.twitter_scraper.requests.get")
    def test_includes_quoted_tweet(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "text": "My take on this",
            "quoted_tweet": {
                "text": "Original tweet content",
                "screen_name": "original_author",
            },
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = fetch_article_content("https://x.com/user/status/12345")
        assert "My take on this" in result
        assert "Original tweet content" in result
        assert "@original_author" in result

    @patch.dict("os.environ", {}, clear=True)
    def test_returns_empty_when_no_api_key(self):
        result = fetch_article_content("https://x.com/user/status/12345")
        assert result == ""

    @patch.dict("os.environ", {"RAPIDAPI_KEY": "test-key"})
    @patch("src.scrapers.twitter_scraper.requests.get")
    def test_returns_empty_on_error(self, mock_get):
        mock_get.side_effect = Exception("timeout")
        result = fetch_article_content("https://x.com/user/status/12345")
        assert result == ""
