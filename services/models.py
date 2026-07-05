"""Shared data model for all trend services."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TrendItem:
    """One entry in a trend list, normalized across every source.

    metrics holds display-ready engagement badges, e.g.
    {"stars": "412,930", "language": "Python"} for GitHub or
    {"likes": "18,204", "downloads": "2.1M"} for Hugging Face.
    """

    rank: int
    title: str
    url: str
    description: str = ""
    metrics: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def fmt_count(value: int | float | None) -> str:
    """Format a raw count as a compact human-readable badge value."""
    if value is None:
        return "0"
    value = int(value)
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 10_000:
        return f"{value / 1_000:.1f}k"
    return f"{value:,}"
