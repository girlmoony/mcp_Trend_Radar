"""GitHub coding trends via the GitHub Search API.

Three views over public repositories:
  - trending:      most-starred repos created in the last 7 days
                   (GitHub has no official "trending" API; this is the
                   standard search-based proxy)
  - most starred:  all-time top repos by stars
  - most forked:   all-time top repos by forks

Set GITHUB_TOKEN to raise the search rate limit from 10 to 30 req/min.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from .http_client import ServiceError, get_json
from .models import TrendItem, fmt_count

SERVICE = "github"
SEARCH_URL = "https://api.github.com/search/repositories"
LIMIT = 20
TRENDING_WINDOW_DAYS = 7


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _search(query: str, sort: str, limit: int) -> list[TrendItem]:
    payload = get_json(
        SERVICE,
        SEARCH_URL,
        params={"q": query, "sort": sort, "order": "desc", "per_page": limit},
        headers=_headers(),
    )
    repos = payload.get("items") or []
    if not repos:
        raise ServiceError(SERVICE, f"search returned no repositories for: {query}")

    items: list[TrendItem] = []
    for rank, repo in enumerate(repos[:limit], start=1):
        items.append(
            TrendItem(
                rank=rank,
                title=repo["full_name"],
                url=repo["html_url"],
                description=(repo.get("description") or "").strip()[:200],
                metrics={
                    "stars": fmt_count(repo.get("stargazers_count")),
                    "forks": fmt_count(repo.get("forks_count")),
                    "language": repo.get("language") or "—",
                },
            )
        )
    return items


def get_github_trends(limit: int = LIMIT) -> list[TrendItem]:
    """Top trending repos: most stars among repos created in the last week."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=TRENDING_WINDOW_DAYS)
    return _search(f"created:>{cutoff.date().isoformat()}", sort="stars", limit=limit)


def get_github_most_starred(limit: int = LIMIT) -> list[TrendItem]:
    """All-time most starred public repositories."""
    return _search("stars:>10000", sort="stars", limit=limit)


def get_github_most_forked(limit: int = LIMIT) -> list[TrendItem]:
    """All-time most forked public repositories."""
    return _search("forks:>5000", sort="forks", limit=limit)
