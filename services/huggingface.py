"""Hugging Face model trends via the public Hub API.

The Hub's list endpoint accepts sort=trendingScore (what the website's
"Trending" tab uses) and sort=likes. Anonymous access works; HF_TOKEN is
honored if present.
"""

from __future__ import annotations

import os

from .http_client import ServiceError, get_json
from .models import TrendItem, fmt_count

SERVICE = "huggingface"
API_URL = "https://huggingface.co/api/models"
LIMIT = 20


def _headers() -> dict[str, str]:
    token = os.environ.get("HF_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _fetch(sort: str, limit: int) -> list[TrendItem]:
    payload = get_json(
        SERVICE,
        API_URL,
        params={"sort": sort, "direction": -1, "limit": limit},
        headers=_headers(),
    )
    if not isinstance(payload, list) or not payload:
        raise ServiceError(SERVICE, f"model list for sort={sort} was empty")

    items: list[TrendItem] = []
    for rank, model in enumerate(payload[:limit], start=1):
        model_id = model.get("id") or model.get("modelId", "unknown")
        pipeline = model.get("pipeline_tag") or "model"
        library = model.get("library_name") or ""
        description = pipeline.replace("-", " ")
        if library:
            description += f" · {library}"
        items.append(
            TrendItem(
                rank=rank,
                title=model_id,
                url=f"https://huggingface.co/{model_id}",
                description=description,
                metrics={
                    "likes": fmt_count(model.get("likes")),
                    "downloads": fmt_count(model.get("downloads")),
                    "task": pipeline,
                },
            )
        )
    return items


def get_hf_trending_models(limit: int = LIMIT) -> list[TrendItem]:
    """Top trending models (the Hub's trendingScore ranking)."""
    return _fetch("trendingScore", limit)


def get_hf_most_liked_models(limit: int = LIMIT) -> list[TrendItem]:
    """All-time most liked models on the Hub."""
    return _fetch("likes", limit)
