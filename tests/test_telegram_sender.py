"""Tests for the telegram_sender module."""

from unittest.mock import patch, Mock

from src.telegram_sender import send_message, send_source_header, send_article_message, _split_message


class TestSplitMessage:
    def test_short_message_not_split(self):
        assert _split_message("hello") == ["hello"]

    def test_splits_on_newline(self):
        text = "A" * 4000 + "\n" + "B" * 4000
        chunks = _split_message(text)
        assert len(chunks) == 2
        assert chunks[0] == "A" * 4000
        assert chunks[1] == "B" * 4000

    def test_force_splits_without_newline(self):
        text = "A" * 5000
        chunks = _split_message(text, max_length=4096)
        assert len(chunks) == 2
        assert len(chunks[0]) == 4096
        assert len(chunks[1]) == 904

    def test_multiple_chunks(self):
        text = ("X" * 3000 + "\n") * 3
        chunks = _split_message(text, max_length=4096)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 4096


class TestSendMessage:
    @patch("src.telegram_sender.requests.post")
    def test_sends_with_html_parse_mode(self, mock_post):
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_post.return_value = mock_resp

        with patch.dict("os.environ", {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "456",
        }):
            send_message("Hello <b>world</b>")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["parse_mode"] == "HTML"
        assert call_kwargs["json"]["chat_id"] == "456"
        assert call_kwargs["json"]["text"] == "Hello <b>world</b>"
        assert "bot123:ABC" in mock_post.call_args[0][0]

    @patch("src.telegram_sender.requests.post")
    def test_splits_long_message(self, mock_post):
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_post.return_value = mock_resp

        long_text = "A" * 4000 + "\n" + "B" * 4000

        with patch.dict("os.environ", {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "456",
        }):
            send_message(long_text)

        assert mock_post.call_count == 2


class TestSendSourceHeader:
    @patch("src.telegram_sender.requests.post")
    def test_sends_header_with_emoji_and_name(self, mock_post):
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_post.return_value = mock_resp

        with patch.dict("os.environ", {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "456",
        }):
            send_source_header("\U0001f4f0", "The Batch")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["text"] == "\U0001f4f0 <b>The Batch</b>"
        assert call_kwargs["json"]["parse_mode"] == "HTML"


class TestSendArticleMessage:
    @patch("src.telegram_sender.requests.post")
    def test_sends_article_with_title_link_and_summary(self, mock_post):
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_post.return_value = mock_resp

        with patch.dict("os.environ", {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "456",
        }):
            send_article_message("Test Article", "https://example.com", "Summary text")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        text = call_kwargs["json"]["text"]
        assert '<a href="https://example.com">Test Article</a>' in text
        assert "Summary text" in text

    @patch("src.telegram_sender.requests.post")
    def test_splits_long_article_summary(self, mock_post):
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_post.return_value = mock_resp

        long_summary = "A" * 4000 + "\n" + "B" * 4000

        with patch.dict("os.environ", {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_CHAT_ID": "456",
        }):
            send_article_message("Title", "https://example.com", long_summary)

        assert mock_post.call_count == 2
