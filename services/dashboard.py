"""Trend dashboard generator.

Aggregates all seven trend feeds and renders a single self-contained
index.html: semantic HTML5, custom CSS variables, no JavaScript, no external
assets, print-friendly. A failed feed degrades to an inline error note in its
own card instead of failing the whole page.

Run directly to build and serve locally:

    python -m services.dashboard          # build output/index.html + serve :8000
    python -m services.dashboard --build  # build only
"""

from __future__ import annotations

import html
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import github, google_news, huggingface, x
from .http_client import ServiceError
from .models import TrendItem

logger = logging.getLogger(__name__)

# Anchored to the project folder, not the process cwd — MCP clients like
# Claude Desktop launch servers from an arbitrary working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "index.html"

Fetcher = Callable[[], list[TrendItem]]


@dataclass
class SectionSpec:
    key: str
    title: str
    subtitle: str
    fetcher: Fetcher


@dataclass
class CategorySpec:
    name: str
    tagline: str
    css_class: str  # maps to a per-category accent color
    sections: list[SectionSpec]


@dataclass
class SectionResult:
    spec: SectionSpec
    items: list[TrendItem] = field(default_factory=list)
    error: str | None = None


CATEGORIES: list[CategorySpec] = [
    CategorySpec(
        name="News",
        tagline="What the AI world is talking about right now",
        css_class="cat-news",
        sections=[
            SectionSpec(
                "x_ai_trends", "X · AI Trends",
                "Top AI threads ranked by engagement", x.get_x_ai_trends,
            ),
            SectionSpec(
                "google_news_ai", "Google News · AI Headlines",
                "Latest AI coverage from the official RSS feed",
                google_news.get_google_news_ai_trends,
            ),
        ],
    ),
    CategorySpec(
        name="Coding",
        tagline="Where developer attention is going on GitHub",
        css_class="cat-coding",
        sections=[
            SectionSpec(
                "github_trending", "GitHub · Trending",
                "Most-starred repositories created in the last 7 days",
                github.get_github_trends,
            ),
            SectionSpec(
                "github_most_starred", "GitHub · Most Starred",
                "All-time leaders by stars", github.get_github_most_starred,
            ),
            SectionSpec(
                "github_most_forked", "GitHub · Most Forked",
                "All-time leaders by forks", github.get_github_most_forked,
            ),
        ],
    ),
    CategorySpec(
        name="Models",
        tagline="The models the community is adopting",
        css_class="cat-models",
        sections=[
            SectionSpec(
                "hf_trending", "Hugging Face · Trending",
                "Hot models by trending score", huggingface.get_hf_trending_models,
            ),
            SectionSpec(
                "hf_most_liked", "Hugging Face · Most Liked",
                "All-time community favorites", huggingface.get_hf_most_liked_models,
            ),
        ],
    ),
]


def collect_sections() -> list[tuple[CategorySpec, list[SectionResult]]]:
    """Fetch every feed, capturing per-section errors instead of raising."""
    collected: list[tuple[CategorySpec, list[SectionResult]]] = []
    for category in CATEGORIES:
        results: list[SectionResult] = []
        for spec in category.sections:
            try:
                results.append(SectionResult(spec=spec, items=spec.fetcher()))
            except ServiceError as exc:
                logger.warning("section %s failed: %s", spec.key, exc)
                results.append(SectionResult(spec=spec, error=exc.message))
        collected.append((category, results))
    return collected


# --------------------------------------------------------------------------
# HTML rendering
# --------------------------------------------------------------------------

_CSS = """
:root {
  --bg: #f6f7f9;
  --surface: #ffffff;
  --text: #1a202c;
  --text-muted: #64748b;
  --border: #e2e8f0;
  --badge-bg: #f1f5f9;
  --news: #0369a1;
  --news-soft: #e0f2fe;
  --coding: #6d28d9;
  --coding-soft: #ede9fe;
  --models: #b45309;
  --models-soft: #fef3c7;
  --radius: 12px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f141a;
    --surface: #171e26;
    --text: #e7edf3;
    --text-muted: #94a3b8;
    --border: #2a3644;
    --badge-bg: #222c38;
    --news: #7dd3fc;
    --news-soft: #0c2d40;
    --coding: #c4b5fd;
    --coding-soft: #2a2244;
    --models: #fcd34d;
    --models-soft: #3d2e0e;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 16px/1.55 "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif;
}
a { color: inherit; }
.page {
  display: block;
  max-width: 1180px;
  margin: 0 auto;
  padding: 32px 20px 64px;
}
.masthead { margin-bottom: 36px; }
.masthead h1 {
  margin: 0 0 6px;
  font-size: 34px;
  letter-spacing: -0.02em;
}
.masthead p { margin: 0; color: var(--text-muted); }

.category { margin: 0 0 44px; }
.category-header {
  border-left: 6px solid var(--accent);
  background: var(--accent-soft);
  border-radius: var(--radius);
  padding: 14px 20px;
  margin-bottom: 18px;
}
.category-header h2 { margin: 0; font-size: 22px; color: var(--accent); }
.category-header p { margin: 2px 0 0; font-size: 14px; color: var(--text-muted); }

.cat-news   { --accent: var(--news);   --accent-soft: var(--news-soft); }
.cat-coding { --accent: var(--coding); --accent-soft: var(--coding-soft); }
.cat-models { --accent: var(--models); --accent-soft: var(--models-soft); }

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 18px;
}
.card {
  display: block;
  background: var(--surface);
  border: 1px solid var(--border);
  border-top: 4px solid var(--accent);
  border-radius: var(--radius);
  padding: 18px 20px;
}
.card h3 { margin: 0 0 2px; font-size: 17px; }
.card .card-sub { margin: 0 0 12px; font-size: 13px; color: var(--text-muted); }

.trend-list {
  list-style: none;
  counter-reset: trend;
  margin: 0;
  padding: 0;
}
.trend-list li {
  counter-increment: trend;
  display: block;
  position: relative;
  padding: 9px 0 9px 42px;
  border-top: 1px solid var(--border);
}
.trend-list li::before {
  content: counter(trend);
  position: absolute;
  left: 0;
  top: 11px;
  width: 28px;
  height: 28px;
  line-height: 28px;
  text-align: center;
  font-size: 13px;
  font-weight: 700;
  color: var(--accent);
  background: var(--accent-soft);
  border-radius: 8px;
}
.trend-title {
  display: block;
  font-weight: 600;
  font-size: 14.5px;
  text-decoration: none;
  overflow-wrap: anywhere;
}
.trend-title:hover { color: var(--accent); text-decoration: underline; }
.trend-desc {
  display: block;
  margin-top: 1px;
  font-size: 13px;
  color: var(--text-muted);
  overflow-wrap: anywhere;
}
.badges { display: block; margin-top: 5px; }
.badge {
  display: inline-block;
  margin: 0 6px 4px 0;
  padding: 1px 9px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--badge-bg);
  border: 1px solid var(--border);
  border-radius: 999px;
  white-space: nowrap;
}
.badge b { color: var(--accent); font-weight: 700; }

.section-error {
  padding: 14px;
  border: 1px dashed var(--border);
  border-radius: 8px;
  font-size: 13.5px;
  color: var(--text-muted);
}
footer.colophon {
  margin-top: 20px;
  font-size: 13px;
  color: var(--text-muted);
  text-align: center;
}

@media print {
  body { background: #fff; color: #000; }
  .cards { display: block; }
  .card { break-inside: avoid; margin-bottom: 14px; border-color: #bbb; }
  .trend-title { text-decoration: none; }
}
"""


def _render_item(item: TrendItem) -> str:
    badges = "".join(
        f'<span class="badge">{html.escape(label)} <b>{html.escape(value)}</b></span>'
        for label, value in item.metrics.items()
    )
    description = (
        f'<span class="trend-desc">{html.escape(item.description)}</span>'
        if item.description
        else ""
    )
    return (
        "<li>"
        f'<a class="trend-title" href="{html.escape(item.url, quote=True)}" '
        f'target="_blank" rel="noopener noreferrer">{html.escape(item.title)}</a>'
        f"{description}"
        f'<span class="badges">{badges}</span>'
        "</li>"
    )


def _render_section(result: SectionResult) -> str:
    spec = result.spec
    if result.error:
        body = (
            f'<p class="section-error">⚠ Could not load this feed: '
            f"{html.escape(result.error)}</p>"
        )
    else:
        body = f'<ol class="trend-list">{"".join(_render_item(i) for i in result.items)}</ol>'
    return (
        f'<article class="card" id="{html.escape(spec.key)}">'
        f"<h3>{html.escape(spec.title)}</h3>"
        f'<p class="card-sub">{html.escape(spec.subtitle)}</p>'
        f"{body}"
        "</article>"
    )


def render_html(collected: list[tuple[CategorySpec, list[SectionResult]]]) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    categories_html = []
    for category, results in collected:
        cards = "".join(_render_section(r) for r in results)
        categories_html.append(
            f'<section class="category {category.css_class}">'
            f'<div class="category-header"><h2>{html.escape(category.name)}</h2>'
            f"<p>{html.escape(category.tagline)}</p></div>"
            f'<div class="cards">{cards}</div>'
            "</section>"
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trend Radar — News · Coding · Models</title>
<style>{_CSS}</style>
</head>
<body>
<div class="page">
  <header class="masthead">
    <h1>📡 Trend Radar</h1>
    <p>Top 20 trends across News, Coding, and AI Models · generated {generated_at}</p>
  </header>
  <main>
    {"".join(categories_html)}
  </main>
  <footer class="colophon">
    Sources: X · Google News RSS · GitHub Search API · Hugging Face Hub API
  </footer>
</div>
</body>
</html>
"""


def generate_dashboard(output_path: str | Path = DEFAULT_OUTPUT) -> dict:
    """Fetch all feeds, write index.html, and return a build summary."""
    collected = collect_sections()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(collected), encoding="utf-8")

    sections_summary = {
        result.spec.key: (
            {"items": len(result.items)} if not result.error else {"error": result.error}
        )
        for _, results in collected
        for result in results
    }
    return {
        "output": str(path.resolve()),
        "sections": sections_summary,
        "total_items": sum(len(r.items) for _, rs in collected for r in rs),
    }


def _serve(directory: Path, port: int = 8000) -> None:
    import functools
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(directory))
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        print(f"Serving dashboard at http://127.0.0.1:{port}/ (Ctrl+C to stop)")
        server.serve_forever()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    summary = generate_dashboard()
    print(f"Built {summary['output']} ({summary['total_items']} items)")
    if "--build" not in sys.argv:
        _serve(Path(summary["output"]).parent)
