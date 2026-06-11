from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SKILLS_DIR = PROJECT_ROOT / "skills"


@pytest.fixture(scope="session")
def registry():
    from skill_runtime import SkillRegistry

    return SkillRegistry(SKILLS_DIR).load_all(strict=True)


@pytest.fixture
def tmp_skill(tmp_path):
    """Factory for throwaway skill dirs with arbitrary SKILL.md content."""

    def _make(name: str, skill_md: str, scripts: dict[str, str] | None = None):
        skill_dir = tmp_path / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
        for fname, code in (scripts or {}).items():
            scripts_dir = skill_dir / "scripts"
            scripts_dir.mkdir(exist_ok=True)
            (scripts_dir / fname).write_text(code, encoding="utf-8")
        return skill_dir

    return _make
