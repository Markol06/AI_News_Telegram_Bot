"""Tests for Reddit scraper (search across all subreddits)."""

from unittest.mock import patch, MagicMock

from src.scrapers.reddit_scraper import (
    fetch_reddit_articles,
    _search_reddit,
    fetch_article_content,
    AI_QUERIES,
    MAX_POSTS,
    USER_AGENT,
)


def _make_reddit_post(i, subreddit="MachineLearning", score=100):
    return {
        "data": {
            "title": f"Post {i}",
            "permalink": f"/r/{subreddit}/comments/abc{i}/post_{i}/",
            "score": score,
            "selftext": f"Self text for post {i}",
            "subreddit": subreddit,
        }
    }


def _make_search_response(posts):
    return {"data": {"children": posts}}


class TestSearchReddit:
    @patch("src.scrapers.reddit_scraper.requests.get")
    def test_returns_posts_from_search(self, mock_get):
        posts = [_make_reddit_post(i, score=100 - i) for i in range(3)]
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_search_response(posts)
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _search_reddit("artificial intelligence")

        assert len(result) == 3
        assert result[0]["title"] == "Post 0"
        assert result[0]["subreddit"] == "MachineLearning"
        assert result[0]["score"] == 100
        assert "reddit.com" in result[0]["url"]
        assert result[0]["content"] == "Self text for post 0"

    @patch("src.scrapers.reddit_scraper.requests.get")
    def test_sends_proper_user_agent(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_search_response([])
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        _search_reddit("AI")

        call_kwargs = mock_get.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert headers["User-Agent"] == USER_AGENT

    @patch("src.scrapers.reddit_scraper.requests.get")
    def test_uses_top_week_params(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _make_search_response([])
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        _search_reddit("machine learning")

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["sort"] == "top"
        assert params["t"] == "week"

    @patch("src.scrapers.reddit_scraper.requests.get")
    def test_returns_empty_on_error(self, mock_get):
        mock_get.side_effect = Exception("Connection error")
        result = _search_reddit("AI")
        assert result == []


class TestFetchRedditArticles:
    @patch("src.scrapers.reddit_scraper._search_reddit")
    def test_searches_all_queries(self, mock_search):
        mock_search.return_value = []
        fetch_reddit_articles()

        assert mock_search.call_count == len(AI_QUERIES)

    @patch("src.scrapers.reddit_scraper._search_reddit")
    def test_deduplicates_by_url(self, mock_search):
        post = {
            "title": "Same post",
            "url": "https://www.reddit.com/r/test/comments/abc/post/",
            "score": 500,
            "content": "",
            "subreddit": "test",
        }
        mock_search.return_value = [post]

        result = fetch_reddit_articles()

        urls = [p["url"] for p in result]
        assert urls.count(post["url"]) == 1

    @patch("src.scrapers.reddit_scraper._search_reddit")
    def test_selects_top_5_by_score(self, mock_search):
        def side_effect(query):
            if "artificial" in query:
                return [
                    {"title": "AI1", "url": "u1", "score": 800, "content": "", "subreddit": "a"},
                    {"title": "AI2", "url": "u2", "score": 100, "content": "", "subreddit": "a"},
                ]
            elif "machine" in query:
                return [
                    {"title": "ML1", "url": "u3", "score": 500, "content": "", "subreddit": "b"},
                    {"title": "ML2", "url": "u4", "score": 200, "content": "", "subreddit": "b"},
                ]
            else:
                return [
                    {"title": "OA1", "url": "u5", "score": 300, "content": "", "subreddit": "c"},
                    {"title": "OA2", "url": "u6", "score": 50, "content": "", "subreddit": "c"},
                ]

        mock_search.side_effect = side_effect

        result = fetch_reddit_articles()

        assert len(result) == MAX_POSTS
        scores = [p["score"] for p in result]
        assert scores == [800, 500, 300, 200, 100]

    @patch("src.scrapers.reddit_scraper._search_reddit")
    def test_caps_at_max_posts(self, mock_search):
        mock_search.return_value = [
            {"title": f"P{i}", "url": f"u{i}", "score": 100 - i, "content": "", "subreddit": "test"}
            for i in range(10)
        ]

        result = fetch_reddit_articles()
        assert len(result) == MAX_POSTS

    @patch("src.scrapers.reddit_scraper._search_reddit")
    def test_handles_empty_results(self, mock_search):
        mock_search.return_value = []
        result = fetch_reddit_articles()
        assert result == []


class TestFetchArticleContent:
    @patch("src.scrapers.reddit_scraper.requests.get")
    def test_extracts_selftext_and_comments(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"data": {"children": [{"data": {"selftext": "Post body here"}}]}},
            {"data": {"children": [
                {"data": {"body": "Comment 1"}},
                {"data": {"body": "Comment 2"}},
                {"data": {"body": "Comment 3"}},
                {"data": {"body": "Comment 4 (should be excluded)"}},
            ]}},
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = fetch_article_content("https://www.reddit.com/r/test/comments/abc/post/")

        assert "Post body here" in result
        assert "Comment 1" in result
        assert "Comment 2" in result
        assert "Comment 3" in result
        assert "Comment 4" not in result

    @patch("src.scrapers.reddit_scraper.requests.get")
    def test_appends_json_to_url(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"data": {"children": [{"data": {"selftext": ""}}]}},
            {"data": {"children": []}},
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        fetch_article_content("https://www.reddit.com/r/test/comments/abc/post/")

        called_url = mock_get.call_args.args[0]
        assert called_url.endswith(".json")

    @patch("src.scrapers.reddit_scraper.requests.get")
    def test_returns_empty_on_error(self, mock_get):
        mock_get.side_effect = Exception("timeout")
        result = fetch_article_content("https://www.reddit.com/r/test/comments/abc/post/")
        assert result == ""

    @patch("src.scrapers.reddit_scraper.requests.get")
    def test_handles_post_without_selftext(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"data": {"children": [{"data": {"selftext": ""}}]}},
            {"data": {"children": [{"data": {"body": "Only comment"}}]}},
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = fetch_article_content("https://www.reddit.com/r/test/comments/abc/post/")
        assert result == "Only comment"
