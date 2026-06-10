"""Skill registry: discovers skills, resolves their tools, builds ADK agents' inputs.

Design notes
------------
- Skill directories follow agentskills.io naming (hyphens), so they are not
  importable Python packages. Script modules are loaded by file path with
  importlib instead.
- Tool resolution is convention-based, because the spec's frontmatter has no
  tool-declaration field: every name in `allowed-tools` must be a function
  defined in exactly one module under the skill's scripts/ directory. The
  function's own docstring is what the LLM sees.
- Progressive disclosure: `instruction_for()` returns the SKILL.md body (level
  2 of the spec's loading model) plus an on-demand resource index; references
  and assets are only read if the agent asks for them via the shared
  `read_skill_resource` tool.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Callable, Dict, List

from skill_runtime.manifest import SkillManifest, SkillValidationError, parse_skill_md

logger = logging.getLogger(__name__)


class ToolResolutionError(RuntimeError):
    """Raised when an allowed-tool cannot be resolved to a script function."""


@dataclass(frozen=True)
class ResolvedTool:
    name: str
    skill_name: str
    func: Callable
    source_file: Path


class SkillRegistry:
    """Loads agentskills.io skill packages and vends their tools to ADK agents."""

    def __init__(self, skills_dir: str | Path) -> None:
        self.skills_dir = Path(skills_dir).resolve()
        self._manifests: Dict[str, SkillManifest] = {}
        self._tools: Dict[str, ResolvedTool] = {}

    # ── Loading ───────────────────────────────────────────────────────────────

    def load_all(self, strict: bool = True) -> "SkillRegistry":
        """Discover and load every skill under skills_dir.

        strict=True (production default): any invalid skill aborts startup.
        strict=False: invalid skills are logged and skipped.
        """
        if not self.skills_dir.is_dir():
            raise FileNotFoundError(f"skills directory not found: {self.skills_dir}")

        candidates = [
            d for d in sorted(self.skills_dir.iterdir())
            if d.is_dir() and (d / "SKILL.md").is_file()
        ]
        if not candidates:
            raise FileNotFoundError(f"no skills found under {self.skills_dir}")

        for skill_dir in candidates:
            try:
                self._load_skill(skill_dir)
            except (SkillValidationError, ToolResolutionError):
                if strict:
                    raise
                logger.exception("Skipping invalid skill at %s", skill_dir)

        logger.info(
            "Loaded %d skill(s), %d tool(s): %s",
            len(self._manifests), len(self._tools), ", ".join(self._tools),
        )
        return self

    def _load_skill(self, skill_dir: Path) -> None:
        manifest = parse_skill_md(skill_dir)

        for tool_name in manifest.allowed_tools:
            resolved = self._resolve_tool(manifest, tool_name)
            if tool_name in self._tools:
                existing = self._tools[tool_name]
                raise ToolResolutionError(
                    f"tool name collision: '{tool_name}' is provided by both "
                    f"'{existing.skill_name}' and '{manifest.name}'"
                )
            self._tools[tool_name] = resolved

        self._manifests[manifest.name] = manifest
        logger.debug("Loaded skill %r (%d tool(s))", manifest.name, len(manifest.allowed_tools))

    def _resolve_tool(self, manifest: SkillManifest, tool_name: str) -> ResolvedTool:
        scripts_dir = manifest.scripts_dir
        if not scripts_dir.is_dir():
            raise ToolResolutionError(
                f"skill '{manifest.name}' declares allowed-tool '{tool_name}' "
                f"but has no scripts/ directory"
            )

        matches: List[tuple[Path, Callable]] = []
        for script in sorted(scripts_dir.glob("*.py")):
            module = _load_module_from_path(manifest.name, script)
            fn = getattr(module, tool_name, None)
            if callable(fn):
                matches.append((script, fn))

        if not matches:
            raise ToolResolutionError(
                f"skill '{manifest.name}': no function named '{tool_name}' found "
                f"in {scripts_dir}/*.py"
            )
        if len(matches) > 1:
            files = ", ".join(str(p.name) for p, _ in matches)
            raise ToolResolutionError(
                f"skill '{manifest.name}': '{tool_name}' is defined in multiple "
                f"scripts ({files}); it must be unique"
            )

        source_file, fn = matches[0]
        if not (fn.__doc__ or "").strip():
            raise ToolResolutionError(
                f"skill '{manifest.name}': '{tool_name}' in {source_file.name} has "
                "no docstring — the LLM needs one to use the tool correctly"
            )
        return ResolvedTool(
            name=tool_name, skill_name=manifest.name, func=fn, source_file=source_file
        )

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def skill_names(self) -> List[str]:
        return list(self._manifests)

    @property
    def tool_names(self) -> List[str]:
        return list(self._tools)

    def manifest(self, skill_name: str) -> SkillManifest:
        try:
            return self._manifests[skill_name]
        except KeyError:
            raise KeyError(
                f"skill '{skill_name}' not loaded; available: {self.skill_names}"
            ) from None

    def tools_for(self, skill_name: str) -> List[Callable]:
        """Plain callables for a skill's allowed-tools, for Agent(tools=[...]).

        ADK wraps bare callables in FunctionTool automatically, deriving the
        schema from signatures and docstrings.
        """
        manifest = self.manifest(skill_name)
        return [self._tools[t].func for t in manifest.allowed_tools]

    # ── Progressive disclosure ────────────────────────────────────────────────

    def catalog(self) -> str:
        """Level 1: name + description for every skill (~100 tokens each)."""
        lines = [
            f"- {m.name}: {m.description}" for m in self._manifests.values()
        ]
        return "Available skills:\n" + "\n".join(lines)

    def instruction_for(self, skill_name: str) -> str:
        """Level 2: the full SKILL.md body, plus an index of level-3 resources."""
        manifest = self.manifest(skill_name)
        resources = manifest.resource_files()
        instruction = manifest.body
        if resources:
            listing = "\n".join(
                f"- {p.relative_to(manifest.skill_dir)}" for p in resources
            )
            instruction += (
                "\n\n## Available skill resources\n\n"
                "Load these on demand with the read_skill_resource tool — only "
                "when the instructions above tell you to, or you need detail "
                "they don't cover:\n" + listing
            )
        return instruction

    def make_resource_reader(self) -> Callable:
        """Level 3: a shared tool that reads references/ and assets/ on demand."""
        registry = self

        def read_skill_resource(skill_name: str, relative_path: str) -> str:
            """Read a reference or asset file bundled with a skill.

            Args:
                skill_name: Name of the skill (e.g. 'web-search').
                relative_path: Path relative to the skill root, e.g.
                    'references/search_guidelines.md' or 'assets/result_template.json'.

            Returns:
                The file's text content.
            """
            manifest = registry.manifest(skill_name)
            target = (manifest.skill_dir / relative_path).resolve()
            # Constrain reads to the skill's own references/ and assets/
            allowed_roots = (manifest.references_dir.resolve(), manifest.assets_dir.resolve())
            if not any(target.is_relative_to(root) for root in allowed_roots):
                return (
                    f"ERROR: '{relative_path}' is outside this skill's "
                    "references/ and assets/ directories."
                )
            if not target.is_file():
                available = "\n".join(
                    str(p.relative_to(manifest.skill_dir)) for p in manifest.resource_files()
                )
                return f"ERROR: file not found. Available resources:\n{available}"
            return target.read_text(encoding="utf-8")

        return read_skill_resource


# ── Module loading ────────────────────────────────────────────────────────────

def _load_module_from_path(skill_name: str, script: Path) -> ModuleType:
    """Import a script by file path (skill dirs contain hyphens, so no package imports)."""
    module_name = f"_skill_{skill_name.replace('-', '_')}_{script.stem}"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        raise ToolResolutionError(f"cannot create import spec for {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        del sys.modules[module_name]
        raise ToolResolutionError(f"failed to import {script}: {exc}") from exc
    return module
