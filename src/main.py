"""Main entry point for AI News Telegram Summary."""

import sys

from dotenv import load_dotenv

from src.scrapers.batch_scraper import fetch_articles, fetch_article_content
from src.scrapers.anthropic_scraper import (
    fetch_anthropic_articles,
    fetch_article_content as fetch_anthropic_content,
)
from src.scrapers.twitter_scraper import (
    fetch_twitter_articles,
    fetch_article_content as fetch_twitter_content,
)
from src.scrapers.reddit_scraper import (
    fetch_reddit_articles,
    fetch_article_content as fetch_reddit_content,
)
from src.history import load_sent_articles, save_sent_articles, filter_new_articles
from src.summarizer import summarize_articles
from src.telegram_sender import send_source_header, send_article_message


# Each source is a dict with keys: name, emoji, fetch, fetch_content
SOURCES = [
    {
        "name": "The Batch",
        "emoji": "\U0001f4f0",
        "fetch": lambda: fetch_articles(limit=10),
        "fetch_content": lambda article: fetch_article_content(article["url"]),
    },
    {
        "name": "Anthropic Blog",
        "emoji": "\U0001f9e0",
        "fetch": fetch_anthropic_articles,
        "fetch_content": lambda article: fetch_anthropic_content(article["url"]),
    },
    {
        "name": "Twitter/X",
        "emoji": "\U0001d54f",
        "fetch": fetch_twitter_articles,
        "fetch_content": lambda article: fetch_twitter_content(article["url"]),
    },
    {
        "name": "Reddit",
        "emoji": "\U0001f4ac",
        "fetch": fetch_reddit_articles,
        "fetch_content": lambda article: fetch_reddit_content(article["url"]),
    },
]


def process_source(source):
    """Process a single source: fetch, dedup, summarize, send.

    Returns the list of new article URLs that were sent, or empty list.
    """
    name = source["name"]
    emoji = source["emoji"]

    print(f"\n--- {emoji} {name} ---")

    print(f"  [1/4] Fetching articles from {name}...")
    try:
        articles = source["fetch"]()
    except Exception as e:
        print(f"  Error fetching articles: {e}")
        return []

    print(f"        Found {len(articles)} articles.")

    print(f"  [2/4] Filtering out already-sent articles...")
    new_articles = filter_new_articles(articles)

    if not new_articles:
        print("        No new articles. Skipping.")
        return []

    print(f"        {len(new_articles)} new article(s) to process.")

    print(f"  [3/4] Fetching content & summarizing...")
    articles_with_content = []
    for article in new_articles:
        try:
            content = source["fetch_content"](article)
            articles_with_content.append({
                "title": article["title"],
                "url": article["url"],
                "content": content,
            })
        except Exception as e:
            print(f"        SKIP {article['title'][:40]}: {e}")

    if not articles_with_content:
        print("        No content fetched. Skipping.")
        return []

    try:
        summaries = summarize_articles(articles_with_content)
    except Exception as e:
        print(f"  Error summarizing: {e}")
        return []

    print(f"  [4/4] Sending to Telegram...")
    try:
        send_source_header(emoji, name)
        for item in summaries:
            send_article_message(item["title"], item["url"], item["summary"])
    except Exception as e:
        print(f"  Error sending to Telegram: {e}")
        return []

    return [a["url"] for a in new_articles]


def main():
    load_dotenv()

    all_sent_urls = []

    for source in SOURCES:
        sent_urls = process_source(source)
        all_sent_urls.extend(sent_urls)

    if all_sent_urls:
        sent = load_sent_articles()
        sent.update(all_sent_urls)
        save_sent_articles(sent)
        print(f"\nDone! Sent {len(all_sent_urls)} article(s) total.")
    else:
        print("\nNo new articles across all sources.")


if __name__ == "__main__":
    main()
