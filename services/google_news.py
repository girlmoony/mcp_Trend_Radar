"""Google News AI trends via the official RSS feed, parsed with feedparser."""

from __future__ import annotations

import feedparser

from .http_client import ServiceError, get
from .models import TrendItem

SERVICE = "google_news"
FEED_URL = (
    "https://news.google.com/rss/search"
    "?q=artificial+intelligence+OR+%22AI%22&hl=en-US&gl=US&ceid=US:en"
)
LIMIT = 20


def get_google_news_ai_trends(limit: int = LIMIT) -> list[TrendItem]:
    """Top AI headlines from the Google News RSS feed."""
    # Fetch with requests first so we get real timeout/HTTP error handling
    # (feedparser swallows network errors into feed.bozo).
    response = get(SERVICE, FEED_URL)
    feed = feedparser.parse(response.content)

    if feed.bozo and not feed.entries:
        raise ServiceError(SERVICE, f"feed could not be parsed: {feed.bozo_exception}")
    if not feed.entries:
        raise ServiceError(SERVICE, "feed contained no entries")

    items: list[TrendItem] = []
    for rank, entry in enumerate(feed.entries[:limit], start=1):
        source = entry.get("source", {}).get("title", "Google News")
        published = entry.get("published", "")
        items.append(
            TrendItem(
                rank=rank,
                title=entry.get("title", "(untitled)"),
                url=entry.get("link", FEED_URL),
                description=f"{source} · {published}",
                metrics={"source": source},
            )
        )
    return items
