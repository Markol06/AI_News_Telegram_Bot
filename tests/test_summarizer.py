"""Tests for the summarizer module."""

from unittest.mock import patch, Mock, MagicMock

from src.summarizer import summarize_articles


SAMPLE_ARTICLES = [
    {
        "title": "Gemini Seizes the Lead",
        "url": "https://www.deeplearning.ai/the-batch/issue-342/",
        "content": "Google updated its flagship Gemini model, topping several benchmarks.",
    },
    {
        "title": "The New Open-Weights Leader",
        "url": "https://www.deeplearning.ai/the-batch/issue-341/",
        "content": "A new open-weights model surpasses previous leaders in benchmarks.",
    },
]


def _make_mock_response(summary_text):
    mock_choice = Mock()
    mock_choice.message.content = summary_text
    mock_response = Mock()
    mock_response.choices = [mock_choice]
    return mock_response


class TestSummarizeArticles:
    @patch("src.summarizer.OpenAI")
    def test_returns_list_of_dicts_with_per_article_summaries(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        summaries = ["Саммері статті 1", "Саммері статті 2"]
        mock_client.chat.completions.create.side_effect = [
            _make_mock_response(s) for s in summaries
        ]

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            result = summarize_articles(SAMPLE_ARTICLES)

        assert isinstance(result, list)
        assert len(result) == 2

        assert result[0]["title"] == "Gemini Seizes the Lead"
        assert result[0]["url"] == "https://www.deeplearning.ai/the-batch/issue-342/"
        assert result[0]["summary"] == "Саммері статті 1"

        assert result[1]["title"] == "The New Open-Weights Leader"
        assert result[1]["url"] == "https://www.deeplearning.ai/the-batch/issue-341/"
        assert result[1]["summary"] == "Саммері статті 2"

    @patch("src.summarizer.OpenAI")
    def test_makes_one_gpt_call_per_article(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_client.chat.completions.create.side_effect = [
            _make_mock_response("s1"), _make_mock_response("s2")
        ]

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            summarize_articles(SAMPLE_ARTICLES)

        assert mock_client.chat.completions.create.call_count == 2

    @patch("src.summarizer.OpenAI")
    def test_each_call_contains_individual_article_data(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_client.chat.completions.create.side_effect = [
            _make_mock_response("s1"), _make_mock_response("s2")
        ]

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            summarize_articles(SAMPLE_ARTICLES)

        calls = mock_client.chat.completions.create.call_args_list

        # First call should contain first article
        user_msg_1 = calls[0][1]["messages"][1]["content"]
        assert "Gemini Seizes the Lead" in user_msg_1
        assert "issue-342" in user_msg_1

        # Second call should contain second article
        user_msg_2 = calls[1][1]["messages"][1]["content"]
        assert "The New Open-Weights Leader" in user_msg_2
        assert "issue-341" in user_msg_2

    @patch("src.summarizer.OpenAI")
    def test_system_prompt_requests_ukrainian(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_client.chat.completions.create.side_effect = [
            _make_mock_response("s1"), _make_mock_response("s2")
        ]

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            summarize_articles(SAMPLE_ARTICLES)

        call_kwargs = mock_client.chat.completions.create.call_args_list[0][1]
        system_msg = call_kwargs["messages"][0]["content"]
        assert "українською" in system_msg

    @patch("src.summarizer.OpenAI")
    def test_uses_correct_model(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_client.chat.completions.create.side_effect = [
            _make_mock_response("s1"), _make_mock_response("s2")
        ]

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            summarize_articles(SAMPLE_ARTICLES)

        call_kwargs = mock_client.chat.completions.create.call_args_list[0][1]
        assert call_kwargs["model"] == "gpt-4o-mini"
