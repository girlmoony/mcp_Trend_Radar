"""Shared HTTP helpers and the common error type for all services."""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20  # seconds
USER_AGENT = "trend-radar-mcp/1.0 (+https://github.com/girlmoony)"


class ServiceError(Exception):
    """Raised by any service when a fetch fails; carries the service name."""

    def __init__(self, service: str, message: str) -> None:
        self.service = service
        self.message = message
        super().__init__(f"[{service}] {message}")


def get(
    service: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> requests.Response:
    """GET a URL, translating every failure mode into ServiceError."""
    merged_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    try:
        response = requests.get(
            url, params=params, headers=merged_headers, timeout=timeout
        )
        response.raise_for_status()
        return response
    except requests.exceptions.Timeout as exc:
        raise ServiceError(service, f"request timed out after {timeout}s: {url}") from exc
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        raise ServiceError(service, f"HTTP {status} from {url}") from exc
    except requests.exceptions.RequestException as exc:
        raise ServiceError(service, f"request failed: {exc}") from exc


def get_json(
    service: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    """GET a URL and parse the JSON body, raising ServiceError on any failure."""
    response = get(service, url, params=params, headers=headers, timeout=timeout)
    try:
        return response.json()
    except ValueError as exc:
        raise ServiceError(service, f"invalid JSON response from {url}") from exc
