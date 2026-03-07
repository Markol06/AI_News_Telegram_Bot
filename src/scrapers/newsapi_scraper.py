"""Scraper for AI news articles via NewsAPI (with GNews fallback)."""

import os
from datetime import datetime, timedelta, timezone

import requests

NEWSAPI_URL = "https://newsapi.org/v2/everything"
GNEWS_URL = "https://gnews.io/api/v4/search"

AI_QUERY = (
    '"artificial intelligence" OR "machine learning" OR "LLM" '
    'OR "generative AI" OR "OpenAI" OR "Anthropic" '
    'OR "Google AI" OR "GPT" OR "Claude"'
)

GNEWS_QUERY = "artificial intelligence OR machine learning OR LLM OR generative AI"

MAX_ARTICLES = 5


def fetch_newsapi_articles(days=7):
    """Fetch top AI news articles from NewsAPI, with GNews fallback.

    Returns a list of dicts: {title, url, date, content}.
    """
    articles = _fetch_from_newsapi(days)

    if len(articles) < MAX_ARTICLES:
        gnews_articles = _fetch_from_gnews(days)
        seen_urls = {a["url"] for a in articles}
        for article in gnews_articles:
            if article["url"] not in seen_urls:
                articles.append(article)
                seen_urls.add(article["url"])
            if len(articles) >= MAX_ARTICLES:
                break

    return articles[:MAX_ARTICLES]


def _fetch_from_newsapi(days):
    """Fetch articles from NewsAPI everything endpoint."""
    api_key = os.environ.get("NEWSAPI_KEY", "")
    if not api_key:
        print("  Warning: NEWSAPI_KEY not set")
        return []

    from_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        response = requests.get(
            NEWSAPI_URL,
            params={
                "q": AI_QUERY,
                "from": from_date,
                "sortBy": "popularity",
                "pageSize": MAX_ARTICLES,
                "language": "en",
                "apiKey": api_key,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"  Warning: NewsAPI request failed: {e}")
        return []

    if data.get("status") != "ok":
        print(f"  Warning: NewsAPI returned status: {data.get('status')}")
        return []

    return [
        {
            "title": a.get("title", ""),
            "url": a.get("url", ""),
            "date": a.get("publishedAt", ""),
            "content": a.get("description") or a.get("content") or "",
        }
        for a in data.get("articles", [])
    ]


def _fetch_from_gnews(days):
    """Fetch articles from GNews as fallback."""
    api_key = os.environ.get("GNEWS_API_KEY", "")
    if not api_key:
        print("  Warning: GNEWS_API_KEY not set")
        return []

    from_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        response = requests.get(
            GNEWS_URL,
            params={
                "q": GNEWS_QUERY,
                "from": from_date,
                "sortby": "relevance",
                "max": MAX_ARTICLES,
                "lang": "en",
                "token": api_key,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"  Warning: GNews request failed: {e}")
        return []

    return [
        {
            "title": a.get("title", ""),
            "url": a.get("url", ""),
            "date": a.get("publishedAt", ""),
            "content": a.get("description") or a.get("content") or "",
        }
        for a in data.get("articles", [])
    ]


def fetch_article_content(url):
    """Fetch article content from URL (uses page text extraction)."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"  Warning: failed to fetch {url}: {e}")
        return ""

    from bs4 import BeautifulSoup
    import re

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    content = soup.find("article") or soup.find("main") or soup.find("body")
    if not content:
        return ""

    text = content.get_text(separator=" ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
