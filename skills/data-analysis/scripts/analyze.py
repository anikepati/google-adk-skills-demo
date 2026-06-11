"""Analysis tool for the data-analysis skill (agentskills.io package)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger("skills.data-analysis")

_MAX_FINDINGS = 6
_TOP_SOURCES = 5


def analyze_results(results_json: str, topic: str, focus_areas: str = "") -> str:
    """Analyse a JSON array of search results into a structured analysis.

    Args:
        results_json: JSON array of search results, each with title, url,
            snippet, and source fields (output of the web-search skill).
        topic: The original research topic, used for relevance scoring.
        focus_areas: Optional comma-separated aspects to emphasise,
            e.g. "hardware,error correction".

    Returns:
        JSON object string with summary, key_findings, entities, sources,
        confidence, and gaps fields (see the skill's references/analysis_schema.json).
        Returns a JSON error object {"error": "..."} for malformed input.
    """
    if not (topic or "").strip():
        return json.dumps({"error": "topic must be a non-empty string"})

    try:
        results = json.loads(results_json)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.error("Malformed results_json: %s", exc)
        return json.dumps({"error": f"results_json is not valid JSON: {exc}"})

    if isinstance(results, dict) and "error" in results:
        # Upstream search failed; propagate rather than analyse the error object
        return json.dumps({"error": f"upstream search error: {results['error']}"})
    if not isinstance(results, list):
        return json.dumps({"error": "results_json must be a JSON array of search results"})

    focus = [f.strip() for f in (focus_areas or "").split(",") if f.strip()]
    analysis = _analyze(results, topic.strip(), focus)
    logger.info(
        "Analysed %d result(s) for %r: %d finding(s), confidence %.2f",
        len(results), topic, len(analysis["key_findings"]), analysis["confidence"],
    )
    return json.dumps(analysis, ensure_ascii=False, indent=2)


def _analyze(results: List[Dict[str, Any]], topic: str, focus_areas: List[str]) -> Dict[str, Any]:
    sources = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "relevance": _score_relevance(r, topic),
        }
        for r in results
    ]
    sources.sort(key=lambda s: s["relevance"], reverse=True)

    snippets = [r.get("snippet", "") for r in results if r.get("snippet")]
    key_findings = _extract_key_points(snippets, topic, focus_areas)
    entities = _extract_entities(" ".join(snippets))
    gaps = _identify_gaps(key_findings, focus_areas)
    confidence = _compute_confidence(sources, key_findings) if results else 0.0

    return {
        "summary": _build_summary(topic, key_findings, bool(results)),
        "key_findings": key_findings,
        "entities": entities,
        "sources": sources[:_TOP_SOURCES],
        "confidence": confidence,
        "gaps": gaps,
    }


def _score_relevance(result: Dict[str, Any], topic: str) -> float:
    topic_words = set(topic.lower().split())
    text = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
    hits = sum(1 for w in topic_words if w in text)
    return round(min(hits / max(len(topic_words), 1), 1.0), 2)


def _extract_key_points(snippets: List[str], topic: str, focus_areas: List[str]) -> List[str]:
    keywords = set(topic.lower().split()) | {f.lower() for f in focus_areas}
    seen: set[str] = set()
    findings: List[str] = []

    for snippet in snippets:
        for sentence in re.split(r"[.!?]", snippet):
            sentence = sentence.strip()
            if len(sentence) <= 40 or not any(kw in sentence.lower() for kw in keywords):
                continue
            key = sentence[:60].lower()
            if key in seen:
                continue
            seen.add(key)
            findings.append(sentence)
            if len(findings) >= _MAX_FINDINGS:
                return findings

    return findings or ["No specific findings extracted — review source snippets directly."]


def _extract_entities(text: str) -> Dict[str, List[str]]:
    seen: set[str] = set()
    concepts: List[str] = []
    for word in text.split():
        cleaned = word.strip(".,!?\"'()")
        if len(cleaned) > 2 and cleaned[0].isupper() and cleaned not in seen:
            seen.add(cleaned)
            concepts.append(cleaned)
        if len(concepts) >= 8:
            break
    return {"concepts": concepts, "people": [], "orgs": [], "places": []}


def _identify_gaps(findings: List[str], focus_areas: List[str]) -> List[str]:
    return [
        f"No clear findings for focus area: '{area}'"
        for area in focus_areas
        if not any(area.lower() in f.lower() for f in findings)
    ]


def _compute_confidence(sources: List[Dict[str, Any]], findings: List[str]) -> float:
    avg_relevance = sum(s["relevance"] for s in sources) / len(sources) if sources else 0.0
    finding_score = min(len(findings) / 5, 1.0)
    return round(avg_relevance * 0.6 + finding_score * 0.4, 2)


def _build_summary(topic: str, findings: List[str], had_results: bool) -> str:
    if not had_results:
        return f"No search results were available for '{topic}'; analysis is empty."
    return (
        f"Analysis of '{topic}' surfaced {len(findings)} key finding(s). "
        "Review key_findings and sources for details. "
        "Confidence reflects source relevance and finding density."
    )
