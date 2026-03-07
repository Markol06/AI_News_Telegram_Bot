"""Scraper for top AI posts from Reddit (r/MachineLearning, r/artificial, r/LocalLLaMA)."""

import time

import requests

SUBREDDITS = ["MachineLearning", "artificial", "LocalLLaMA"]
MAX_POSTS = 5
USER_AGENT = "AI-News-Bot/1.0"


def fetch_reddit_articles():
    """Fetch top-5 posts by score across all subreddits (last 7 days).

    Returns a list of dicts: {title, url, score, content, subreddit}.
    """
    all_posts = []
    for subreddit in SUBREDDITS:
        posts = _fetch_subreddit(subreddit)
        all_posts.extend(posts)
        time.sleep(1)

    all_posts.sort(key=lambda p: p["score"], reverse=True)
    return all_posts[:MAX_POSTS]


def _fetch_subreddit(subreddit):
    """Fetch top posts from a single subreddit over the last week."""
    url = f"https://www.reddit.com/r/{subreddit}/top.json"
    try:
        response = requests.get(
            url,
            params={"t": "week", "limit": 25},
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"  Warning: Reddit r/{subreddit} request failed: {e}")
        return []

    posts = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        posts.append({
            "title": post.get("title", ""),
            "url": f"https://www.reddit.com{post.get('permalink', '')}",
            "score": post.get("score", 0),
            "content": post.get("selftext", ""),
            "subreddit": subreddit,
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
