"""Spec-compliance tests for SKILL.md parsing and validation."""

import pytest

from skill_runtime.manifest import SkillValidationError, parse_skill_md

VALID = """---
name: {name}
description: Does a thing. Use when the user wants the thing done.
---

# Instructions

Do the thing.
"""


def test_minimal_valid_skill(tmp_skill):
    d = tmp_skill("my-skill", VALID.format(name="my-skill"))
    m = parse_skill_md(d)
    assert m.name == "my-skill"
    assert m.body.startswith("# Instructions")
    assert m.allowed_tools == []


def test_name_must_match_directory(tmp_skill):
    d = tmp_skill("wrong-dir", VALID.format(name="my-skill"))
    with pytest.raises(SkillValidationError, match="must match the parent directory"):
        parse_skill_md(d)


@pytest.mark.parametrize("bad", ["My-Skill", "-skill", "skill-", "a--b", "has_underscore"])
def test_invalid_names_rejected(tmp_skill, bad):
    d = tmp_skill(bad, VALID.format(name=bad))
    with pytest.raises(SkillValidationError):
        parse_skill_md(d)


def test_missing_description_rejected(tmp_skill):
    d = tmp_skill("no-desc", "---\nname: no-desc\n---\nbody")
    with pytest.raises(SkillValidationError, match="description"):
        parse_skill_md(d)


def test_description_over_1024_rejected(tmp_skill):
    md = f"---\nname: long-desc\ndescription: {'x' * 1025}\n---\nbody"
    with pytest.raises(SkillValidationError, match="1024"):
        parse_skill_md(tmp_skill("long-desc", md))


def test_unknown_frontmatter_field_rejected(tmp_skill):
    md = (
        "---\nname: extra-field\ndescription: ok desc\ntools:\n  - nope\n---\nbody"
    )
    with pytest.raises(SkillValidationError, match="unknown frontmatter"):
        parse_skill_md(tmp_skill("extra-field", md))


def test_nested_metadata_rejected(tmp_skill):
    md = (
        "---\nname: nested-meta\ndescription: ok desc\n"
        "metadata:\n  outer:\n    inner: 1\n---\nbody"
    )
    with pytest.raises(SkillValidationError, match="string-to-string"):
        parse_skill_md(tmp_skill("nested-meta", md))


def test_allowed_tools_parsed_as_space_separated(tmp_skill):
    md = (
        "---\nname: multi-tool\ndescription: ok desc\n"
        "allowed-tools: tool_a tool_b\n---\nbody"
    )
    m = parse_skill_md(tmp_skill("multi-tool", md))
    assert m.allowed_tools == ["tool_a", "tool_b"]


def test_missing_frontmatter_rejected(tmp_skill):
    d = tmp_skill("no-fm", "# just markdown, no frontmatter")
    with pytest.raises(SkillValidationError, match="frontmatter"):
        parse_skill_md(d)
