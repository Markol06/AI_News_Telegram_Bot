# AI News Telegram Bot

Multi-source AI news pipeline that:
- fetches articles/posts from **The Batch**, **Anthropic Blog**, and **Twitter/X**
- summarizes each item with OpenAI
- sends one message per article to Telegram, grouped by source header
- deduplicates already sent URLs via `sent_articles.json`

## Features

- Per-source processing with fixed order:
  1. The Batch
  2. Anthropic Blog
  3. Twitter/X
- Ukrainian summaries for Telegram
- HTML-safe Telegram message format
- Source isolation: one source failing does not stop the rest

## Requirements

- Python 3.10+
- Telegram bot token + chat ID
- OpenAI API key
- RapidAPI key (for Twitter/X scraper)

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

1. Copy `.env.example` to `.env`
2. Fill required values:

```env
OPENAI_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
RAPIDAPI_KEY=...
```

## Run

```bash
python -m src.main
```

## Tests

```bash
pytest tests -q
```

## Project Structure

- `src/main.py` - pipeline entry point and source orchestration
- `src/scrapers/` - source-specific fetchers
- `src/summarizer.py` - OpenAI summarization logic
- `src/telegram_sender.py` - Telegram message delivery helpers
- `src/history.py` - deduplication state management
