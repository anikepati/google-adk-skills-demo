"""Research pipeline orchestrator using Google ADK + agentskills.io skills.

Progressive disclosure (per the agentskills.io spec):
  Level 1 — the root agent sees only each skill's name + description (catalog).
  Level 2 — each sub-agent's instruction IS its skill's SKILL.md body.
  Level 3 — references/ and assets/ are loaded on demand via read_skill_resource.

Pipeline: user query → web-search → data-analysis → report-writer
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.agents import Agent, SequentialAgent

from skill_runtime import SkillRegistry

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_MODEL = os.getenv("ADK_MODEL", "gemini-2.0-flash")
_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

# Strict: an invalid SKILL.md aborts startup rather than degrading silently.
registry = SkillRegistry(_SKILLS_DIR).load_all(strict=True)
read_skill_resource = registry.make_resource_reader()


def _skill_agent(agent_name: str, skill_name: str) -> Agent:
    """Build an ADK agent whose behaviour is defined entirely by its skill package."""
    manifest = registry.manifest(skill_name)
    return Agent(
        name=agent_name,
        model=_MODEL,
        description=manifest.description,           # level 1: from frontmatter
        instruction=registry.instruction_for(skill_name),  # level 2: SKILL.md body
        tools=[*registry.tools_for(skill_name), read_skill_resource],  # level 3 access
    )


web_search_agent = _skill_agent("web_search_agent", "web-search")
data_analysis_agent = _skill_agent("data_analysis_agent", "data-analysis")
report_writer_agent = _skill_agent("report_writer_agent", "report-writer")

research_pipeline = SequentialAgent(
    name="research_pipeline",
    description=(
        "End-to-end research pipeline: searches the web, analyses the results, "
        "and produces a polished Markdown report."
    ),
    sub_agents=[web_search_agent, data_analysis_agent, report_writer_agent],
)

root_agent = Agent(
    name="research_orchestrator",
    model=_MODEL,
    description="Orchestrates a multi-step research pipeline for any topic.",
    instruction=(
        "You are a research orchestrator.\n\n"
        f"{registry.catalog()}\n\n"
        "When the user asks you to research a topic, delegate the full task to "
        "the research_pipeline sub-agent, which runs the skills above in "
        "sequence. Present the final Markdown report to the user verbatim."
    ),
    sub_agents=[research_pipeline],
)
