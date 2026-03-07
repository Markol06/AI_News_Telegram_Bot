"""Tests for the history module."""

import json
import os
from unittest.mock import patch

from src.history import load_sent_articles, save_sent_articles, filter_new_articles


class TestLoadSentArticles:
    def test_returns_empty_set_if_file_missing(self, tmp_path):
        fake_path = str(tmp_path / "nonexistent.json")
        with patch("src.history.HISTORY_FILE", fake_path):
            result = load_sent_articles()
        assert result == set()

    def test_loads_urls_from_file(self, tmp_path):
        fake_path = str(tmp_path / "sent.json")
        with open(fake_path, "w") as f:
            json.dump(["https://a.com/1", "https://a.com/2"], f)

        with patch("src.history.HISTORY_FILE", fake_path):
            result = load_sent_articles()

        assert result == {"https://a.com/1", "https://a.com/2"}


class TestSaveSentArticles:
    def test_writes_urls_to_file(self, tmp_path):
        fake_path = str(tmp_path / "sent.json")
        urls = {"https://a.com/2", "https://a.com/1"}

        with patch("src.history.HISTORY_FILE", fake_path):
            save_sent_articles(urls)

        with open(fake_path) as f:
            data = json.load(f)

        assert data == ["https://a.com/1", "https://a.com/2"]  # sorted

    def test_overwrites_existing_file(self, tmp_path):
        fake_path = str(tmp_path / "sent.json")
        with open(fake_path, "w") as f:
            json.dump(["https://old.com"], f)

        with patch("src.history.HISTORY_FILE", fake_path):
            save_sent_articles({"https://new.com"})

        with open(fake_path) as f:
            data = json.load(f)

        assert data == ["https://new.com"]


class TestFilterNewArticles:
    def test_filters_out_sent_articles(self, tmp_path):
        fake_path = str(tmp_path / "sent.json")
        with open(fake_path, "w") as f:
            json.dump(["https://a.com/1"], f)

        articles = [
            {"title": "Old", "url": "https://a.com/1", "date": ""},
            {"title": "New", "url": "https://a.com/2", "date": ""},
        ]

        with patch("src.history.HISTORY_FILE", fake_path):
            result = filter_new_articles(articles)

        assert len(result) == 1
        assert result[0]["title"] == "New"

    def test_returns_all_when_no_history(self, tmp_path):
        fake_path = str(tmp_path / "nonexistent.json")
        articles = [
            {"title": "A", "url": "https://a.com/1", "date": ""},
            {"title": "B", "url": "https://a.com/2", "date": ""},
        ]

        with patch("src.history.HISTORY_FILE", fake_path):
            result = filter_new_articles(articles)

        assert len(result) == 2
