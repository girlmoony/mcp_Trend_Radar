"""Trend Radar — an MCP server for News, Coding, and AI Model trends.

Tools (all return JSON):
  News:    get_x_ai_trends, get_google_news_ai_trends
  Coding:  get_github_trends, get_github_most_starred, get_github_most_forked
  Models:  get_hf_trending_models, get_hf_most_liked_models
  Web:     generate_trends_dashboard  (aggregates everything into index.html)

Run:  python server.py            (stdio transport, for MCP clients)
Dev:  mcp dev server.py           (MCP Inspector)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from services import dashboard, github, google_news, huggingface, x
from services.http_client import ServiceError
from services.models import TrendItem

# Load .env from the project folder regardless of the client's launch cwd.
load_dotenv(Path(__file__).resolve().parent / ".env")
logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
logger = logging.getLogger("trend-radar")

mcp = FastMCP("trend-radar")


def _tool_response(
    source: str, fetcher: Callable[[], list[TrendItem]], **extra: object
) -> str:
    """Run a fetcher and serialize the result (or a structured error) as JSON."""
    try:
        items = fetcher()
        payload: dict[str, object] = {
            "source": source,
            "count": len(items),
            "items": [item.to_dict() for item in items],
            **extra,
        }
    except ServiceError as exc:
        logger.error("%s failed: %s", source, exc)
        payload = {"source": source, "error": exc.message, "items": []}
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- News ----

@mcp.tool()
def get_x_ai_trends() -> str:
    """Top 20 AI trends/threads on X (Twitter), ranked by engagement.

    Returns live data when X_BEARER_TOKEN is configured; otherwise a curated
    mock list with identical structure (flagged via "data_mode").
    """
    mode = "live" if x.has_credentials() else "mock"
    return _tool_response("x_ai_trends", x.get_x_ai_trends, data_mode=mode)


@mcp.tool()
def get_google_news_ai_trends() -> str:
    """Top 20 AI headlines parsed from the official Google News RSS feed."""
    return _tool_response("google_news_ai", google_news.get_google_news_ai_trends)


# -------------------------------------------------------------- Coding ----

@mcp.tool()
def get_github_trends() -> str:
    """Top 20 trending GitHub repositories (most stars, created in last 7 days)."""
    return _tool_response("github_trending", github.get_github_trends)


@mcp.tool()
def get_github_most_starred() -> str:
    """Top 20 most starred repositories of all time via the GitHub Search API."""
    return _tool_response("github_most_starred", github.get_github_most_starred)


@mcp.tool()
def get_github_most_forked() -> str:
    """Top 20 most forked repositories of all time via the GitHub Search API."""
    return _tool_response("github_most_forked", github.get_github_most_forked)


# -------------------------------------------------------------- Models ----

@mcp.tool()
def get_hf_trending_models() -> str:
    """Top 20 trending models on Hugging Face (Hub trendingScore ranking)."""
    return _tool_response("hf_trending", huggingface.get_hf_trending_models)


@mcp.tool()
def get_hf_most_liked_models() -> str:
    """Top 20 most liked models on Hugging Face of all time."""
    return _tool_response("hf_most_liked", huggingface.get_hf_most_liked_models)


# ----------------------------------------------------------- Dashboard ----

@mcp.tool()
def generate_trends_dashboard(output_path: str = "") -> str:
    """Aggregate all 7 trend feeds and generate a polished HTML dashboard.

    Writes a fully self-contained index.html (no JS, no external assets) with
    colored sections per platform, numbered lists, and engagement badges.
    Individual feed failures appear as inline notes instead of failing the
    build. Returns a JSON build summary with the absolute output path.

    Args:
        output_path: Where to write the HTML file. Defaults to
            <project>/output/index.html; relative paths resolve against the
            project folder.
    """
    try:
        target = Path(output_path) if output_path else dashboard.DEFAULT_OUTPUT
        if not target.is_absolute():
            target = dashboard.PROJECT_ROOT / target
        summary = dashboard.generate_dashboard(target)
        summary["hint"] = (
            "Open the file directly in a browser, or serve it with: "
            "python -m services.dashboard"
        )
        return json.dumps(summary, ensure_ascii=False, indent=2)
    except OSError as exc:
        logger.error("dashboard write failed: %s", exc)
        return json.dumps({"error": f"could not write dashboard: {exc}"})


if __name__ == "__main__":
    mcp.run()
