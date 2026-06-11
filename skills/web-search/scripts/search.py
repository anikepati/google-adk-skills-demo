"""Web search tool for the web-search skill (agentskills.io package)."""

from __future__ import annotations

import json
import logging
import time
from typing import List
from urllib.parse import urlparse

logger = logging.getLogger("skills.web-search")

_MAX_RESULTS_CAP = 20
_RETRY_DELAY_S = 2.0


def search_web(query: str, max_results: int = 5) -> str:
    """Search the web and return a JSON array of results.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (1-20, default 5).

    Returns:
        JSON array string; each element has title, url, snippet, and source
        (domain) fields. Returns a JSON error object on failure:
        {"error": "...", "query": "..."}.
    """
    query = (query or "").strip()
    if not query:
        return json.dumps({"error": "query must be a non-empty string", "query": query})
    max_results = max(1, min(int(max_results), _MAX_RESULTS_CAP))

    try:
        results = _run_search(query, max_results)
        if not results:
            # DuckDuckGo rate-limits informally; one retry after a short pause
            logger.warning("Empty results for %r; retrying once", query)
            time.sleep(_RETRY_DELAY_S)
            results = _run_search(query, max_results)
    except Exception as exc:
        logger.exception("Search failed for %r", query)
        return json.dumps({"error": f"search failed: {exc}", "query": query})

    logger.info("Search %r returned %d result(s)", query, len(results))
    return json.dumps(results, ensure_ascii=False, indent=2)


def _run_search(query: str, max_results: int) -> List[dict]:
    # Imported lazily so the registry can load this module without the
    # dependency installed (e.g. during validation or offline tests).
    from duckduckgo_search import DDGS

    results: List[dict] = []
    with DDGS() as ddgs:
        for hit in ddgs.text(query, max_results=max_results):
            url = hit.get("href", "")
            results.append(
                {
                    "title": hit.get("title", ""),
                    "url": url,
                    "snippet": hit.get("body", ""),
                    "source": _extract_domain(url),
                }
            )
    return results


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc
    except ValueError:
        return url
