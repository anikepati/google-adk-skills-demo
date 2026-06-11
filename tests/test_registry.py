"""Tests for skill discovery, tool resolution, and progressive disclosure."""

import pytest

from skill_runtime import SkillRegistry
from skill_runtime.registry import ToolResolutionError

TOOL_SKILL = """---
name: {name}
description: A test skill. Use for testing.
allowed-tools: {tools}
---

Body instructions here.
"""


def test_bundled_skills_load(registry):
    assert sorted(registry.skill_names) == ["data-analysis", "report-writer", "web-search"]
    assert sorted(registry.tool_names) == ["analyze_results", "generate_report", "search_web"]


def test_tools_for_returns_callables(registry):
    tools = registry.tools_for("data-analysis")
    assert len(tools) == 1 and callable(tools[0])
    assert tools[0].__name__ == "analyze_results"


def test_catalog_contains_all_skills(registry):
    catalog = registry.catalog()
    for name in registry.skill_names:
        assert name in catalog


def test_instruction_is_skill_md_body_plus_resources(registry):
    instr = registry.instruction_for("web-search")
    assert "Web Search Skill" in instr
    assert "references/search_guidelines.md" in instr


def test_resource_reader_reads_and_blocks_traversal(registry):
    reader = registry.make_resource_reader()
    ok = reader("web-search", "references/search_guidelines.md")
    assert ok.startswith("# Web Search Guidelines")
    blocked = reader("web-search", "../data-analysis/SKILL.md")
    assert blocked.startswith("ERROR")
    missing = reader("web-search", "references/nope.md")
    assert missing.startswith("ERROR: file not found")


def test_missing_tool_function_fails_strict(tmp_skill):
    tmp_skill("ghost-tool", TOOL_SKILL.format(name="ghost-tool", tools="not_there"),
              scripts={"impl.py": "def other():\n    '''doc'''\n"})
    reg = SkillRegistry(tmp_skill("x", TOOL_SKILL.format(name="x", tools="")).parent)
    with pytest.raises(ToolResolutionError, match="not_there"):
        reg.load_all(strict=True)


def test_tool_without_docstring_rejected(tmp_skill):
    d = tmp_skill("bare-fn", TOOL_SKILL.format(name="bare-fn", tools="bare"),
                  scripts={"impl.py": "def bare(x: str) -> str:\n    return x\n"})
    with pytest.raises(ToolResolutionError, match="docstring"):
        SkillRegistry(d.parent).load_all(strict=True)


def test_non_strict_skips_invalid_skills(tmp_skill):
    tmp_skill("good-one", TOOL_SKILL.format(name="good-one", tools=""))
    bad = tmp_skill("bad-one", TOOL_SKILL.format(name="bad-one", tools="missing_fn"))
    reg = SkillRegistry(bad.parent).load_all(strict=False)
    assert reg.skill_names == ["good-one"]
