"""Scraper for The Neuron Daily newsletter via RSS feed."""

import re
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

RSS_URL = "https://rss.beehiiv.com/feeds/N4eCstxvgX.xml"


def fetch_neuron_articles(days=7):
    """Fetch recent articles from The Neuron Daily RSS feed.

    Returns a list of dicts with keys: title, url, date.
    Only includes articles published within the last `days` days.
    """
    response = requests.get(RSS_URL, timeout=30)
    response.raise_for_status()

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    articles = []

    soup = BeautifulSoup(response.text, "xml")
    items = soup.find_all("item")

    for item in items:
        title = item.find("title")
        link = item.find("link")
        pub_date = item.find("pubDate")

        if not title or not link:
            continue

        title_text = title.get_text(strip=True)
        url = link.get_text(strip=True)
        date_str = pub_date.get_text(strip=True) if pub_date else ""

        if date_str:
            parsed_date = _parse_rfc2822(date_str)
            if parsed_date and parsed_date < cutoff:
                continue

        articles.append({
            "title": title_text,
            "url": url,
            "date": date_str,
        })

    return articles


def fetch_article_content(url):
    """Fetch and extract text content from a Neuron Daily article page.

    Returns clean text suitable for summarization.
    """
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove non-content elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    content = soup.find("article") or soup.find("main") or soup.find("body")
    if not content:
        return ""

    return _html_to_text(str(content))


def _html_to_text(html):
    """Convert HTML to clean text, preserving section structure."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    for hr in soup.find_all("hr"):
        hr.replace_with("\n---\n")

    for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
        heading.insert_before("\n\n")
        heading.insert_after("\n")

    text = soup.get_text(separator=" ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_rfc2822(date_str):
    """Parse an RFC 2822 date string to a timezone-aware datetime."""
    # e.g. "Fri, 27 Mar 2026 08:35:00 +0000"
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except Exception:
        return None
