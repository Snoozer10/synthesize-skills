#!/usr/bin/env python3
"""Skill Creator & Scaffolding Engine (Pure Python Standard Library)."""

import argparse
import os
import pathlib
import re
import sys

# Windows UTF-8 console output hardening
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate_skill_name(name: str) -> None:
    if not NAME_PATTERN.match(name):
        raise ValueError(
            f"Invalid skill name '{name}'. Must be lowercase kebab-case matching '^[a-z0-9]+(-[a-z0-9]+)*$' "
            f"(e.g., 'data-autocleaning', 'release-sync'). No underscores, uppercase, or double hyphens."
        )


def generate_skill_content(name: str, description: str, keywords: list[str]) -> str:
    desc = description.strip()
    if not desc.startswith("Use when"):
        desc = f"Use when {desc[0].lower() + desc[1:]}" if desc else "Use when performing tasks with this skill."

    # Clamp description to 500 chars per validator spec
    if len(desc) > 500:
        desc = desc[:497] + "..."

    kw_line = ", ".join(keywords) if keywords else f"{name}, skill, agent"

    content = f"""---
name: {name}
description: {desc}
---

# {name}

Provides capabilities and automated tooling for {name}.

## Overview
Detailed instructions for agent task execution and deterministic verification.

## Operations
```bash
# Execute sample operation
python scripts/run.py --help
```

```powershell
# Windows PowerShell invocation
python scripts/run.py --help
```

## Keywords
{kw_line}
"""
    return content


def scaffold_skill(name: str, dest_dir: pathlib.Path, description: str, keywords: list[str]) -> pathlib.Path:
    validate_skill_name(name)

    skill_path = dest_dir / name
    if skill_path.exists():
        raise FileExistsError(f"Directory '{skill_path}' already exists.")

    skill_path.mkdir(parents=True, exist_ok=True)
    scripts_dir = skill_path / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    references_dir = skill_path / "references"
    references_dir.mkdir(exist_ok=True)

    # Write starter script
    run_py = scripts_dir / "run.py"
    run_py.write_text(
        '#!/usr/bin/env python3\n"""Sample runner."""\nimport sys\n\ndef main():\n    print("Skill active.")\n\nif __name__ == "__main__":\n    main()\n',
        encoding="utf-8",
    )

    # Write SKILL.md
    skill_md = skill_path / "SKILL.md"
    skill_content = generate_skill_content(name, description, keywords)
    skill_md.write_text(skill_content, encoding="utf-8")

    return skill_path


def main():
    parser = argparse.ArgumentParser(description="Scaffold a new agent skill adhering to agentskills.io standards.")
    parser.add_argument("name", help="Skill name in lowercase kebab-case (e.g., 'code-auditor')")
    parser.add_argument("--dest", default=".agents/skills", help="Destination parent directory (default: '.agents/skills')")
    parser.add_argument("--desc", default="", help="Description starting with 'Use when...'")
    parser.add_argument("--keywords", default="", help="Comma-separated keywords")

    args = parser.parse_args()

    try:
        dest_path = pathlib.Path(args.dest).resolve()
        kw_list = [k.strip() for k in args.keywords.split(",") if k.strip()]
        created = scaffold_skill(args.name, dest_path, args.desc, kw_list)
        print(f"Scaffolded skill '{args.name}' at: {created}")
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
