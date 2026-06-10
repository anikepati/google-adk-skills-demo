"""SKILL.md parsing and validation per the agentskills.io specification.

Spec: https://agentskills.io/specification

Frontmatter fields (the only ones the spec defines):
  name          required  1-64 chars, [a-z0-9-], no leading/trailing/double hyphen,
                          must match parent directory name
  description   required  1-1024 chars
  license       optional
  compatibility optional  1-500 chars
  metadata      optional  string -> string map
  allowed-tools optional  space-separated string (experimental)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import yaml

logger = logging.getLogger(__name__)

_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}

# Spec recommendation: keep SKILL.md under 500 lines / body under ~5000 tokens.
_MAX_BODY_LINES = 500


class SkillValidationError(ValueError):
    """Raised when a SKILL.md violates the agentskills.io specification."""

    def __init__(self, path: Path, errors: List[str]) -> None:
        self.path = path
        self.errors = errors
        bullet_list = "\n".join(f"  - {e}" for e in errors)
        super().__init__(f"{path} is not a valid agentskills.io skill:\n{bullet_list}")


@dataclass(frozen=True)
class SkillManifest:
    """Parsed and validated SKILL.md."""

    name: str
    description: str
    body: str                       # Markdown instructions after the frontmatter
    skill_dir: Path
    license: str = ""
    compatibility: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)
    allowed_tools: List[str] = field(default_factory=list)

    @property
    def scripts_dir(self) -> Path:
        return self.skill_dir / "scripts"

    @property
    def references_dir(self) -> Path:
        return self.skill_dir / "references"

    @property
    def assets_dir(self) -> Path:
        return self.skill_dir / "assets"

    def resource_files(self) -> List[Path]:
        """All on-demand resources (references/ and assets/), per the spec."""
        files: List[Path] = []
        for d in (self.references_dir, self.assets_dir):
            if d.is_dir():
                files.extend(p for p in sorted(d.rglob("*")) if p.is_file())
        return files


def parse_skill_md(skill_dir: Path) -> SkillManifest:
    """Parse and validate skill_dir/SKILL.md. Raises SkillValidationError."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        raise SkillValidationError(skill_md, ["SKILL.md not found"])

    text = skill_md.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(skill_md, text)

    errors = validate_manifest(frontmatter, body, skill_dir)
    if errors:
        raise SkillValidationError(skill_md, errors)

    allowed_raw = frontmatter.get("allowed-tools", "") or ""
    metadata_raw = frontmatter.get("metadata") or {}

    manifest = SkillManifest(
        name=frontmatter["name"],
        description=frontmatter["description"].strip(),
        body=body.strip(),
        skill_dir=skill_dir.resolve(),
        license=str(frontmatter.get("license", "") or ""),
        compatibility=str(frontmatter.get("compatibility", "") or "").strip(),
        metadata={str(k): str(v) for k, v in metadata_raw.items()},
        allowed_tools=allowed_raw.split(),
    )
    logger.debug("Parsed skill %r from %s", manifest.name, skill_dir)
    return manifest


def validate_manifest(frontmatter: dict, body: str, skill_dir: Path) -> List[str]:
    """Return a list of spec violations (empty list = valid)."""
    errors: List[str] = []

    name = frontmatter.get("name")
    if not name or not isinstance(name, str):
        errors.append("'name' is required and must be a string")
    else:
        if len(name) > 64:
            errors.append(f"'name' exceeds 64 characters ({len(name)})")
        if not _NAME_RE.match(name):
            errors.append(
                "'name' may only contain lowercase letters, digits, and single "
                "hyphens, and must not start or end with a hyphen"
            )
        if name != skill_dir.name:
            errors.append(
                f"'name' ({name!r}) must match the parent directory name "
                f"({skill_dir.name!r})"
            )

    description = frontmatter.get("description")
    if not description or not isinstance(description, str) or not description.strip():
        errors.append("'description' is required and must be a non-empty string")
    elif len(description) > 1024:
        errors.append(f"'description' exceeds 1024 characters ({len(description)})")

    compatibility = frontmatter.get("compatibility")
    if compatibility is not None and len(str(compatibility)) > 500:
        errors.append(f"'compatibility' exceeds 500 characters ({len(str(compatibility))})")

    metadata = frontmatter.get("metadata")
    if metadata is not None:
        if not isinstance(metadata, dict):
            errors.append("'metadata' must be a mapping")
        else:
            for k, v in metadata.items():
                if isinstance(v, (dict, list)):
                    errors.append(
                        f"'metadata.{k}' must be a string value (spec requires a "
                        "string-to-string map)"
                    )

    allowed = frontmatter.get("allowed-tools")
    if allowed is not None and not isinstance(allowed, str):
        errors.append("'allowed-tools' must be a space-separated string")

    unknown = set(frontmatter) - _SPEC_FIELDS
    if unknown:
        errors.append(
            f"unknown frontmatter field(s) not in the agentskills.io spec: "
            f"{', '.join(sorted(unknown))}"
        )

    if len(body.splitlines()) > _MAX_BODY_LINES:
        errors.append(
            f"SKILL.md body exceeds the recommended {_MAX_BODY_LINES} lines — "
            "move detail into references/"
        )

    return errors


def _split_frontmatter(path: Path, text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise SkillValidationError(path, ["missing YAML frontmatter (file must start with '---')"])
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise SkillValidationError(path, ["malformed frontmatter (no closing '---')"])
    try:
        frontmatter = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        raise SkillValidationError(path, [f"frontmatter is not valid YAML: {exc}"]) from exc
    if not isinstance(frontmatter, dict):
        raise SkillValidationError(path, ["frontmatter must be a YAML mapping"])
    return frontmatter, parts[2]
