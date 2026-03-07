"""Scraper for Anthropic blog articles across multiple sections."""

import re
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

SECTIONS = [
    "https://www.anthropic.com/research",
    "https://www.anthropic.com/engineering",
    "https://www.anthropic.com/news",
    "https://alignment.anthropic.com",
]

BASE_URLS = {
    "https://www.anthropic.com": "https://www.anthropic.com",
    "https://alignment.anthropic.com": "https://alignment.anthropic.com",
}


def fetch_anthropic_articles(days=7):
    """Fetch recent articles from all Anthropic blog sections.

    Returns a deduplicated list of dicts: {title, url, date, content}.
    Only includes articles published within the last `days` days.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    seen_urls = set()
    articles = []

    for section_url in SECTIONS:
        try:
            section_articles = _scrape_section(section_url, cutoff)
        except Exception as e:
            print(f"  Warning: failed to scrape {section_url}: {e}")
            continue

        for article in section_articles:
            if article["url"] not in seen_urls:
                seen_urls.add(article["url"])
                articles.append(article)

    return articles


def _scrape_section(section_url, cutoff):
    """Scrape a single Anthropic blog section for recent articles."""
    response = requests.get(section_url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    base = _get_base_url(section_url)
    articles = []

    for link in soup.find_all("a", href=True):
        href = link["href"]
        title = link.get_text(strip=True)

        if not title or len(title) < 10:
            continue

        url = _resolve_url(href, base)
        if not url or not _is_article_url(url, base):
            continue

        date_str = _find_date_near(link)
        if not date_str:
            continue

        parsed_date = _parse_date(date_str)
        if not parsed_date or parsed_date < cutoff:
            continue

        articles.append({
            "title": title,
            "url": url,
            "date": parsed_date.isoformat(),
            "content": "",
        })

    return articles


def fetch_article_content(url):
    """Fetch full text content from an Anthropic article page."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()

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


def _get_base_url(section_url):
    """Get the base URL for resolving relative links."""
    if "alignment.anthropic.com" in section_url:
        return "https://alignment.anthropic.com"
    return "https://www.anthropic.com"


def _resolve_url(href, base):
    """Resolve a potentially relative URL to absolute."""
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return f"{base}{href}"
    return None


def _is_article_url(url, base):
    """Check if a URL looks like an article (not a section index or external link)."""
    if base == "https://alignment.anthropic.com":
        return url.startswith(base) and url != base and url != base + "/"
    return (
        url.startswith("https://www.anthropic.com/research/")
        or url.startswith("https://www.anthropic.com/engineering/")
        or url.startswith("https://www.anthropic.com/news/")
    )


def _find_date_near(element):
    """Try to find a date string near a link element."""
    parent = element.parent
    for _ in range(3):
        if parent is None:
            break
        text = parent.get_text(separator=" ")
        date_match = re.search(
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}",
            text,
        )
        if date_match:
            return date_match.group(0)
        parent = parent.parent
    return None


def _parse_date(date_str):
    """Parse a date string like 'Mar 5, 2026' into a datetime."""
    date_str = date_str.replace(",", "")
    for fmt in ("%b %d %Y", "%B %d %Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
