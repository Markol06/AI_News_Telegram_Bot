"""Send messages to Telegram."""

import os
from html import escape

import requests

MAX_MESSAGE_LENGTH = 4096


def _send_raw(text):
    """Send text to the configured Telegram chat using Bot API with HTML parse mode.

    Splits into multiple messages if text exceeds 4096 characters.
    """
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    chunks = _split_message(text)
    for chunk in chunks:
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML",
            },
            timeout=30,
        )
        response.raise_for_status()


# Keep old name as alias for backward compatibility
send_message = _send_raw


def send_source_header(emoji, name):
    """Send a header message for a source section (e.g. '📰 The Batch')."""
    text = f"{emoji} <b>{name}</b>"
    _send_raw(text)


def send_article_message(title, url, summary):
    """Send a single article message with title link and summary.

    Handles long summaries by splitting across multiple messages.
    """
    text = f'<a href="{url}">{escape(title)}</a>\n\n{summary}'
    _send_raw(text)


def _split_message(text, max_length=MAX_MESSAGE_LENGTH):
    """Split text into chunks that fit within Telegram's message limit.

    Tries to split on newlines to avoid breaking mid-sentence.
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break

        # Find last newline within limit
        split_pos = text.rfind("\n", 0, max_length)
        if split_pos == -1:
            # No newline found, force split at max_length
            split_pos = max_length

        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip("\n")

    return chunks
