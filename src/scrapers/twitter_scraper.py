"""Scraper for popular AI tweets via RapidAPI (twitter-api45)."""

import os

import requests

RAPIDAPI_HOST = "twitter-api45.p.rapidapi.com"
SEARCH_URL = f"https://{RAPIDAPI_HOST}/search.php"
TWEET_DETAIL_URL = f"https://{RAPIDAPI_HOST}/tweet.php"

AI_QUERIES = [
    "artificial intelligence OR machine learning OR LLM OR generative AI",
    "OpenAI OR Anthropic OR Google AI OR GPT OR Claude",
]

AI_ACCOUNTS = [
    # Companies
    "OpenAI",         # OpenAI
    "AnthropicAI",    # Anthropic
    "GoogleDeepMind", # Google DeepMind / Gemini
    # Individuals
    "karpathy",       # Andrej Karpathy - ex-Tesla/OpenAI, Eureka Labs
    "AndrewYNg",      # Andrew Ng - DeepLearning.AI, Stanford
    "ylecun",         # Yann LeCun - Chief AI Scientist @ Meta
    "drjimfan",       # Jim Fan - NVIDIA, embodied AI
    "drfeifei",       # Fei-Fei Li - Stanford, computer vision
    "demishassabis",  # Demis Hassabis - CEO Google DeepMind
    "alliekmiller",   # Allie K. Miller - AI Business, ex-Amazon/IBM
    "jeremyphoward",  # Jeremy Howard - fast.ai
    "rasbt",          # Sebastian Raschka - Lightning AI
    "GaryMarcus",     # Gary Marcus - AI critic, author
    "sama",           # Sam Altman - CEO OpenAI
    "trq212",         # Thariq
    "bcherny",        # Boris Cherny
    "felixrieseberg", # Felix Rieseberg
]

MAX_TWEETS = 10


def fetch_twitter_articles():
    """Fetch top AI tweets from the past week using combined approach.

    Searches by keywords and monitors key AI accounts.
    Returns a list of dicts: {title, url, score, content}.
    """
    api_key = os.environ.get("RAPIDAPI_KEY", "")
    if not api_key:
        print("  Warning: RAPIDAPI_KEY not set")
        return []

    all_tweets = {}

    # Fetch by keyword search
    for query in AI_QUERIES:
        tweets = _search_tweets(api_key, query)
        for t in tweets:
            all_tweets[t["url"]] = t

    # Fetch from key AI accounts
    for account in AI_ACCOUNTS:
        tweets = _search_tweets(api_key, f"from:{account}")
        for t in tweets:
            all_tweets[t["url"]] = t

    results = list(all_tweets.values())
    results.sort(key=lambda t: t["score"], reverse=True)
    return results[:MAX_TWEETS]


def _search_tweets(api_key, query):
    """Search tweets via RapidAPI twitter-api45."""
    headers = {
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": api_key,
    }

    try:
        response = requests.get(
            SEARCH_URL,
            params={"query": query, "search_type": "Top"},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"  Warning: Twitter search failed for '{query}': {e}")
        return []

    tweets = []
    timeline = data.get("timeline") or []
    for entry in timeline:
        tweet_id = entry.get("tweet_id") or entry.get("rest_id", "")
        text = entry.get("text", "")
        screen_name = entry.get("screen_name", "")
        favorites = entry.get("favorites", 0) or 0
        retweets = entry.get("retweets", 0) or 0
        replies = entry.get("replies", 0) or 0

        if not tweet_id or not text:
            continue

        engagement = favorites + retweets * 2 + replies
        url = f"https://x.com/{screen_name}/status/{tweet_id}"

        title = text[:100] + ("..." if len(text) > 100 else "")
        title = f"@{screen_name}: {title}"

        tweets.append({
            "title": title,
            "url": url,
            "score": engagement,
            "content": text,
        })

    return tweets


def fetch_article_content(url):
    """Fetch full tweet content via RapidAPI.

    Falls back to the content already fetched during search.
    """
    api_key = os.environ.get("RAPIDAPI_KEY", "")
    if not api_key:
        return ""

    # Extract tweet ID from URL
    parts = url.rstrip("/").split("/")
    tweet_id = parts[-1] if parts else ""
    if not tweet_id:
        return ""

    headers = {
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": api_key,
    }

    try:
        response = requests.get(
            TWEET_DETAIL_URL,
            params={"id": tweet_id},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"  Warning: failed to fetch tweet {url}: {e}")
        return ""

    parts = []
    text = data.get("text", "")
    if text:
        parts.append(text)

    # Include quoted tweet if present
    quoted = data.get("quoted_tweet", {})
    if quoted and quoted.get("text"):
        quoted_author = quoted.get("screen_name", "unknown")
        parts.append(f"[Quoted @{quoted_author}]: {quoted['text']}")

    return "\n\n".join(parts)
