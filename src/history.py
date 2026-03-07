"""Track sent articles to avoid sending duplicates."""

import json
import os

HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sent_articles.json")


def load_sent_articles():
    """Load the set of already-sent article URLs from disk."""
    if not os.path.exists(HISTORY_FILE):
        return set()

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return set(data)


def save_sent_articles(urls):
    """Save the set of sent article URLs to disk."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(urls), f, indent=2)


def filter_new_articles(articles):
    """Return only articles whose URLs have not been sent yet."""
    sent = load_sent_articles()
    return [a for a in articles if a["url"] not in sent]
