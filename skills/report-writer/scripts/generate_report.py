"""Report rendering tool for the report-writer skill (agentskills.io package)."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger("skills.report-writer")

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_TEMPLATE_NAME = "report_template.md"
_FORMATS = ("markdown", "plain")


def generate_report(topic: str, analysis_json: str, format: str = "markdown") -> str:
    """Render a research report from an analysis JSON object.

    Args:
        topic: The research question; becomes the report title.
        analysis_json: JSON object string produced by the data-analysis skill
            (summary, key_findings, entities, sources, confidence, gaps).
        format: Output format, "markdown" (default) or "plain".

    Returns:
        The rendered report as a string. On bad input, returns a short
        "REPORT ERROR: ..." string describing the problem.
    """
    if not (topic or "").strip():
        return "REPORT ERROR: topic must be a non-empty string."
    if format not in _FORMATS:
        return f"REPORT ERROR: format must be one of {_FORMATS}, got {format!r}."

    try:
        analysis = json.loads(analysis_json)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.error("Malformed analysis_json: %s", exc)
        return f"REPORT ERROR: analysis_json is not valid JSON: {exc}"

    if not isinstance(analysis, dict):
        return "REPORT ERROR: analysis_json must be a JSON object."
    if "error" in analysis:
        return f"REPORT ERROR: upstream analysis failed: {analysis['error']}"

    rendered = _render(topic.strip(), analysis)
    if format == "plain":
        rendered = re.sub(r"[#*`|_-]{1,3}", "", rendered)
        rendered = re.sub(r"\n{3,}", "\n\n", rendered).strip()

    logger.info("Rendered %s report for %r (%d chars)", format, topic, len(rendered))
    return rendered


def _render(topic: str, analysis: dict) -> str:
    # Imported lazily so the registry can load this module without jinja2
    # installed (e.g. during validation or offline tests).
    from jinja2 import Environment, FileSystemLoader

    env = Environment(
        loader=FileSystemLoader(_ASSETS_DIR),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,  # output is Markdown, not HTML
    )
    template = env.get_template(_TEMPLATE_NAME)
    return template.render(
        topic=topic,
        summary=analysis.get("summary", ""),
        key_findings=analysis.get("key_findings", []),
        sources=analysis.get("sources", []),
        entities=analysis.get("entities", {}),
        confidence=analysis.get("confidence", 0.0),
        gaps=analysis.get("gaps", []),
    )
