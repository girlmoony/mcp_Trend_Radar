"""X (Twitter) AI trends.

Uses the X API v2 recent-search endpoint when X_BEARER_TOKEN is set; otherwise
serves a curated mock list with the exact same shape, so downstream consumers
(the MCP tool and the dashboard) never need to branch. Swapping mock for live
is purely a matter of exporting the token.
"""

from __future__ import annotations

import os

from .http_client import ServiceError, get_json
from .models import TrendItem, fmt_count

SERVICE = "x"
SEARCH_URL = "https://api.x.com/2/tweets/search/recent"
SEARCH_QUERY = (
    '("AI" OR "artificial intelligence" OR "LLM" OR "machine learning")'
    " -is:retweet -is:reply lang:en"
)
LIMIT = 20


def has_credentials() -> bool:
    return bool(os.environ.get("X_BEARER_TOKEN"))


def get_x_ai_trends(limit: int = LIMIT) -> list[TrendItem]:
    """Top AI trends/threads on X — live when authenticated, mock otherwise."""
    if has_credentials():
        return _fetch_live(limit)
    return _mock_trends(limit)


def _fetch_live(limit: int) -> list[TrendItem]:
    token = os.environ["X_BEARER_TOKEN"]
    payload = get_json(
        SERVICE,
        SEARCH_URL,
        params={
            "query": SEARCH_QUERY,
            "max_results": 100,  # fetch wide, rank by engagement below
            "tweet.fields": "public_metrics,author_id,created_at",
            "expansions": "author_id",
            "user.fields": "username",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    tweets = payload.get("data") or []
    if not tweets:
        raise ServiceError(SERVICE, "recent search returned no tweets")

    users = {
        u["id"]: u.get("username", "unknown")
        for u in payload.get("includes", {}).get("users", [])
    }
    tweets.sort(
        key=lambda t: t.get("public_metrics", {}).get("like_count", 0), reverse=True
    )

    items: list[TrendItem] = []
    for rank, tweet in enumerate(tweets[:limit], start=1):
        metrics = tweet.get("public_metrics", {})
        username = users.get(tweet.get("author_id", ""), "i")
        text = " ".join(tweet.get("text", "").split())
        items.append(
            TrendItem(
                rank=rank,
                title=text[:120] + ("…" if len(text) > 120 else ""),
                url=f"https://x.com/{username}/status/{tweet['id']}",
                description=f"@{username} · {tweet.get('created_at', '')[:10]}",
                metrics={
                    "likes": fmt_count(metrics.get("like_count")),
                    "reposts": fmt_count(metrics.get("retweet_count")),
                    "replies": fmt_count(metrics.get("reply_count")),
                },
            )
        )
    return items


# Curated fallback reflecting recurring AI discussion threads on X. Structured
# identically to live results so API injection is a drop-in replacement.
_MOCK_TOPICS: list[tuple[str, str, int, int]] = [
    ("Claude's new agentic coding benchmarks spark debate over autonomous dev workflows", "AnthropicAI", 48200, 9100),
    ("Open-weights vs closed frontier models — the licensing fight reignites", "ylecun", 41500, 8700),
    ("GPT-class models running locally on consumer GPUs: llama.cpp thread", "ggerganov", 39800, 8200),
    ("Why context windows beyond 1M tokens change RAG architecture forever", "swyx", 35400, 7600),
    ("AI agents booking real flights end-to-end — demo thread", "OpenAI", 33900, 7100),
    ("The GPU shortage economics thread everyone is quoting", "sama", 31200, 6800),
    ("Mixture-of-Experts explained with napkin math", "karpathy", 30100, 6500),
    ("EU AI Act enforcement begins: what actually changes for startups", "EU_Commission", 27600, 6100),
    ("Diffusion vs autoregressive video generation — side-by-side results", "runwayml", 25900, 5800),
    ("Prompt injection is still unsolved: red-team writeup", "simonw", 24700, 5400),
    ("Fine-tuning is dead, long live RAG + long context (spicy take)", "jeremyphoward", 23300, 5100),
    ("Robotics foundation models: one policy, twelve embodiments", "DrJimFan", 22100, 4800),
    ("Small models beating big ones on domain tasks — eval thread", "HuggingFace", 20800, 4500),
    ("The real cost of training a frontier model, itemized", "EpochAIResearch", 19500, 4200),
    ("Speech-to-speech models make voice agents finally usable", "elevenlabsio", 18200, 3900),
    ("AI-generated code in production: 6-month retrospective", "GergelyOrosz", 17400, 3600),
    ("Synthetic data flywheels and model collapse — new paper summary", "arankomatsuzaki", 16100, 3300),
    ("On-device AI: Apple/Qualcomm NPU benchmarks compared", "MaxWinebach", 14900, 3000),
    ("Interpretability breakthrough: tracing circuits in production LLMs", "ch402", 13700, 2800),
    ("The agent eval crisis: why leaderboards disagree with reality", "percyliang", 12600, 2500),
]


def _mock_trends(limit: int) -> list[TrendItem]:
    items: list[TrendItem] = []
    for rank, (title, author, likes, reposts) in enumerate(
        _MOCK_TOPICS[:limit], start=1
    ):
        items.append(
            TrendItem(
                rank=rank,
                title=title,
                url=f"https://x.com/search?q={'+'.join(title.split()[:6])}",
                description=f"@{author} · mock sample (set X_BEARER_TOKEN for live data)",
                metrics={"likes": fmt_count(likes), "reposts": fmt_count(reposts)},
            )
        )
    return items
