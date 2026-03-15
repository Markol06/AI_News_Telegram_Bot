"""Tests for the main module."""

from unittest.mock import patch, call

from src.main import main, process_source, SOURCES


FAKE_ARTICLES = [
    {"title": "Article 1", "url": "https://example.com/1", "date": "2026-01-01"},
    {"title": "Article 2", "url": "https://example.com/2", "date": "2026-01-02"},
]

FAKE_SUMMARIES = [
    {"title": "Article 1", "url": "https://example.com/1", "summary": "<b>Summary 1</b>"},
    {"title": "Article 2", "url": "https://example.com/2", "summary": "<b>Summary 2</b>"},
]


class TestProcessSource:
    @patch("src.main.send_article_message")
    @patch("src.main.send_source_header")
    @patch("src.main.summarize_articles", return_value=FAKE_SUMMARIES)
    @patch("src.main.filter_new_articles", return_value=FAKE_ARTICLES)
    def test_full_source_pipeline(self, mock_filter, mock_summarize, mock_header, mock_article):
        source = {
            "name": "Test Source",
            "emoji": "\U0001f4f0",
            "fetch": lambda: FAKE_ARTICLES,
            "fetch_content": lambda a: "Content for " + a["title"],
        }

        urls = process_source(source)

        assert urls == ["https://example.com/1", "https://example.com/2"]
        mock_filter.assert_called_once()
        mock_summarize.assert_called_once()
        mock_header.assert_called_once_with("\U0001f4f0", "Test Source")
        assert mock_article.call_count == 2
        mock_article.assert_any_call("Article 1", "https://example.com/1", "<b>Summary 1</b>")
        mock_article.assert_any_call("Article 2", "https://example.com/2", "<b>Summary 2</b>")

    @patch("src.main.send_article_message")
    @patch("src.main.send_source_header")
    @patch("src.main.summarize_articles")
    @patch("src.main.filter_new_articles", return_value=[])
    def test_returns_empty_when_no_new_articles(self, mock_filter, mock_summarize, mock_header, mock_article):
        source = {
            "name": "Test Source",
            "emoji": "\U0001f4f0",
            "fetch": lambda: FAKE_ARTICLES,
            "fetch_content": lambda a: "Content",
        }

        urls = process_source(source)

        assert urls == []
        mock_summarize.assert_not_called()
        mock_header.assert_not_called()

    @patch("src.main.send_article_message")
    @patch("src.main.send_source_header")
    @patch("src.main.summarize_articles", return_value=[FAKE_SUMMARIES[0]])
    @patch("src.main.filter_new_articles", return_value=FAKE_ARTICLES)
    def test_skips_articles_with_fetch_errors(self, mock_filter, mock_summarize, mock_header, mock_article):
        call_count = 0

        def fetch_content_with_error(article):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("timeout")
            return "Content"

        source = {
            "name": "Test Source",
            "emoji": "\U0001f4f0",
            "fetch": lambda: FAKE_ARTICLES,
            "fetch_content": fetch_content_with_error,
        }

        urls = process_source(source)

        # Should still process with the one successful article
        assert len(urls) == 2  # all new_articles URLs are tracked
        mock_summarize.assert_called_once()
        articles_arg = mock_summarize.call_args[0][0]
        assert len(articles_arg) == 1
        assert articles_arg[0]["title"] == "Article 1"

    @patch("src.main.send_article_message")
    @patch("src.main.send_source_header")
    @patch("src.main.summarize_articles")
    @patch("src.main.filter_new_articles", return_value=FAKE_ARTICLES)
    def test_returns_empty_on_fetch_error(self, mock_filter, mock_summarize, mock_header, mock_article):
        source = {
            "name": "Test Source",
            "emoji": "\U0001f4f0",
            "fetch": lambda: (_ for _ in ()).throw(Exception("network error")),
            "fetch_content": lambda a: "Content",
        }

        urls = process_source(source)

        assert urls == []
        mock_filter.assert_not_called()


class TestSources:
    def test_sources_has_four_entries(self):
        assert len(SOURCES) == 4

    def test_sources_order(self):
        names = [s["name"] for s in SOURCES]
        assert names == ["The Batch", "Anthropic Blog", "Twitter/X", "Reddit"]

    def test_each_source_has_required_keys(self):
        for source in SOURCES:
            assert "name" in source
            assert "emoji" in source
            assert "fetch" in source
            assert "fetch_content" in source
            assert callable(source["fetch"])
            assert callable(source["fetch_content"])


class TestMain:
    @patch("src.main.save_sent_articles")
    @patch("src.main.load_sent_articles", return_value=set())
    @patch("src.main.process_source", return_value=["https://example.com/1"])
    @patch("src.main.load_dotenv")
    def test_main_saves_sent_urls(self, mock_dotenv, mock_process, mock_load, mock_save):
        main()

        mock_dotenv.assert_called_once()
        assert mock_process.call_count == 4
        mock_save.assert_called_once()
        saved_urls = mock_save.call_args[0][0]
        assert "https://example.com/1" in saved_urls

    @patch("src.main.save_sent_articles")
    @patch("src.main.load_sent_articles")
    @patch("src.main.process_source", return_value=[])
    @patch("src.main.load_dotenv")
    def test_main_skips_save_when_nothing_sent(self, mock_dotenv, mock_process, mock_load, mock_save):
        main()

        assert mock_process.call_count == 4
        mock_save.assert_not_called()

    @patch("src.main.save_sent_articles")
    @patch("src.main.load_sent_articles", return_value=set())
    @patch("src.main.process_source")
    @patch("src.main.load_dotenv")
    def test_main_processes_all_four_sources_in_order(self, mock_dotenv, mock_process, mock_load, mock_save):
        """All 4 sources are processed in the correct order."""
        mock_process.return_value = []

        main()

        assert mock_process.call_count == 4
        source_names = [c[0][0]["name"] for c in mock_process.call_args_list]
        assert source_names == ["The Batch", "Anthropic Blog", "Twitter/X", "Reddit"]
