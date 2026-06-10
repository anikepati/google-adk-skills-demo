"""Validate skill packages against the agentskills.io specification.

Usage:
    python -m skill_runtime.cli validate skills/web-search
    python -m skill_runtime.cli validate skills/        # validate every skill
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from skill_runtime.manifest import SkillValidationError, parse_skill_md


def validate(path: Path) -> int:
    """Validate one skill dir, or every skill under a parent dir. Returns exit code."""
    if (path / "SKILL.md").is_file():
        targets = [path]
    else:
        targets = sorted(
            d for d in path.iterdir() if d.is_dir() and (d / "SKILL.md").is_file()
        )
        if not targets:
            print(f"error: no SKILL.md found in or under {path}", file=sys.stderr)
            return 2

    failures = 0
    for skill_dir in targets:
        try:
            manifest = parse_skill_md(skill_dir)
        except SkillValidationError as exc:
            failures += 1
            print(f"✗ {skill_dir}")
            for err in exc.errors:
                print(f"    {err}")
            continue
        print(f"✓ {manifest.name}  ({skill_dir})")
        if manifest.allowed_tools:
            print(f"    allowed-tools: {' '.join(manifest.allowed_tools)}")

    print(f"\n{len(targets) - failures}/{len(targets)} skill(s) valid")
    return 1 if failures else 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="skill_runtime", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_validate = sub.add_parser("validate", help="validate skill package(s)")
    p_validate.add_argument("path", type=Path, help="skill directory or parent directory")
    args = parser.parse_args()

    if args.command == "validate":
        sys.exit(validate(args.path))


if __name__ == "__main__":
    main()
