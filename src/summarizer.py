"""Generate Ukrainian-language summaries of AI news articles via OpenAI API."""

import os

from openai import OpenAI

MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "Ти — AI-асистент, який створює стислі саммері новин зі сфери AI. "
    "Відповідай ТІЛЬКИ українською мовою. "
    "Формат відповіді — Telegram HTML (дозволені теги: <b>, <i>, <a>, <code>). "
    "НЕ використовуй Markdown."
)

USER_PROMPT_TEMPLATE = (
    "Створи коротке саммері цієї AI-статті. "
    "Перелічи 2-4 ключові теми з короткими описами (1-2 речення кожна).\n\n"
    "Назва: {title}\n"
    "URL: {url}\n"
    "Контент:\n{content}"
)


def summarize_articles(articles_with_content):
    """Summarize each article individually via GPT.

    Each article dict should have: title, url, content.
    Returns list of dicts: [{title, url, summary}, ...].
    """
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    results = []

    for article in articles_with_content:
        user_content = USER_PROMPT_TEMPLATE.format(
            title=article["title"],
            url=article["url"],
            content=article["content"][:3000],
        )

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
        )

        results.append({
            "title": article["title"],
            "url": article["url"],
            "summary": response.choices[0].message.content,
        })

    return results
