"""Scraper for deeplearning.ai/the-batch articles."""

import json
import re

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.deeplearning.ai"
BATCH_URL = f"{BASE_URL}/the-batch/"


def fetch_articles(limit=10):
    """Fetch the latest articles from The Batch.

    Returns a list of dicts with keys: title, url, date.
    """
    response = requests.get(BATCH_URL, timeout=30)
    response.raise_for_status()

    articles = _parse_from_next_data(response.text)
    if not articles:
        articles = _parse_from_html(response.text)

    return articles[:limit]


def _parse_from_next_data(html):
    """Try to parse articles from Next.js __NEXT_DATA__ JSON."""
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return []

    data = json.loads(script.string)
    posts = (
        data.get("props", {})
        .get("pageProps", {})
        .get("posts", [])
    )

    articles = []
    for post in posts:
        title = post.get("title", "").strip()
        slug = post.get("slug", "")
        date = post.get("published_at", "")

        if not title or not slug:
            continue

        # Build absolute URL - slugs may or may not include the-batch prefix
        if slug.startswith("http"):
            url = slug
        elif slug.startswith("/"):
            url = f"{BASE_URL}{slug}"
        else:
            url = f"{BATCH_URL}{slug}/"

        articles.append({"title": title, "url": url, "date": date})

    return articles


def fetch_article_content(url):
    """Fetch and extract text content from an individual Batch issue page.

    Returns clean text with topic sections preserved.
    """
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    # Try __NEXT_DATA__ first
    content = _extract_content_from_next_data(response.text)
    if not content:
        content = _extract_content_from_body(response.text)

    return content


def _extract_content_from_next_data(html):
    """Extract article content from Next.js __NEXT_DATA__ post.html field."""
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        return ""

    data = json.loads(script.string)
    post_html = (
        data.get("props", {})
        .get("pageProps", {})
        .get("post", {})
        .get("html", "")
    )

    if not post_html:
        return ""

    return _html_to_text(post_html)


def _extract_content_from_body(html):
    """Fallback: extract article content from the page body."""
    soup = BeautifulSoup(html, "html.parser")
    # Try common content containers
    content = soup.find("article") or soup.find("main") or soup.find("body")
    if not content:
        return ""
    return _html_to_text(str(content))


def _html_to_text(html):
    """Convert HTML to clean text, preserving section structure."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    # Replace hr with section separator
    for hr in soup.find_all("hr"):
        hr.replace_with("\n---\n")

    # Add newlines around headings
    for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
        heading.insert_before("\n\n")
        heading.insert_after("\n")

    text = soup.get_text(separator=" ")

    # Clean up whitespace: collapse multiple spaces, normalize newlines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_from_html(html):
    """Fallback: parse articles from HTML anchor tags."""
    soup = BeautifulSoup(html, "html.parser")
    articles = []
    seen_urls = set()

    for a_tag in soup.find_all("a", href=re.compile(r"/the-batch/issue-\d+")):
        href = a_tag.get("href", "")
        if href in seen_urls:
            continue
        seen_urls.add(href)

        if href.startswith("/"):
            url = f"{BASE_URL}{href}"
        else:
            url = href

        # Find title text within or near the link
        title = a_tag.get_text(strip=True)
        if not title:
            heading = a_tag.find(["h1", "h2", "h3", "h4"])
            title = heading.get_text(strip=True) if heading else url

        articles.append({"title": title, "url": url, "date": ""})

    return articles
