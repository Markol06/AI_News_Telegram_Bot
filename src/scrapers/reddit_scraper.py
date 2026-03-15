"""Scraper for top AI posts from Reddit (search across all subreddits)."""

import requests

SEARCH_URL = "https://www.reddit.com/search.json"

AI_QUERIES = [
    "artificial intelligence",
    "machine learning OR LLM OR generative AI",
    "OpenAI OR Anthropic OR Google AI OR GPT OR Claude",
]

MAX_POSTS = 5
USER_AGENT = "AI-News-Bot/1.0"


def fetch_reddit_articles():
    """Fetch top-5 AI posts by score across all of Reddit (last 7 days).

    Searches by AI keywords and returns the most popular results.
    Returns a list of dicts: {title, url, score, content, subreddit}.
    """
    all_posts = {}

    for query in AI_QUERIES:
        posts = _search_reddit(query)
        for post in posts:
            all_posts[post["url"]] = post

    results = list(all_posts.values())
    results.sort(key=lambda p: p["score"], reverse=True)
    return results[:MAX_POSTS]


def _search_reddit(query):
    """Search Reddit for top posts matching a query over the last week."""
    try:
        response = requests.get(
            SEARCH_URL,
            params={
                "q": query,
                "sort": "top",
                "t": "week",
                "limit": 25,
                "type": "link",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"  Warning: Reddit search failed for '{query}': {e}")
        return []

    posts = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        posts.append({
            "title": post.get("title", ""),
            "url": f"https://www.reddit.com{post.get('permalink', '')}",
            "score": post.get("score", 0),
            "content": post.get("selftext", ""),
            "subreddit": post.get("subreddit", ""),
        })
    return posts


def fetch_article_content(url):
    """Fetch post content and top comments from a Reddit post URL."""
    json_url = url.rstrip("/") + ".json"
    try:
        response = requests.get(
            json_url,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"  Warning: failed to fetch Reddit post {url}: {e}")
        return ""

    parts = []

    # Post selftext
    if len(data) > 0:
        post_data = data[0].get("data", {}).get("children", [{}])[0].get("data", {})
        selftext = post_data.get("selftext", "")
        if selftext:
            parts.append(selftext)

    # Top comments
    if len(data) > 1:
        comments = data[1].get("data", {}).get("children", [])
        for comment in comments[:3]:
            body = comment.get("data", {}).get("body", "")
            if body:
                parts.append(body)

    return "\n\n".join(parts)
