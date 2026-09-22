#!/usr/bin/env python3
"""
scripts/compile_adapters.py — Multi-Host AI Agent Adapter Compiler
Stdlib only. Compiles canonical skills into host-native adapter files:
- Claude Code slash commands (.claude/commands/)
- Antigravity / Gemini rules (.gemini/rules/)
- Cursor MDC rules (.cursor/rules/*.mdc)
- OpenCode slash commands (.opencode/commands/)
- OpenAI Codex instructions (.codex/instructions/)
- Windsurf rules (.windsurf/rules/)
- GitHub Copilot instructions (.github/copilot-instructions/)
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path


def parse_frontmatter(skill_md: Path) -> dict:
    """Parse YAML frontmatter from a SKILL.md file."""
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    raw_fm = parts[1]
    name_m = re.search(r"^name:\s*([a-z0-9-]+)\s*$", raw_fm, re.MULTILINE)
    desc_m = re.search(r"^description:\s*(.+)$", raw_fm, re.MULTILINE)
    return {
        "name": name_m.group(1).strip() if name_m else skill_md.parent.name,
        "description": desc_m.group(1).strip() if desc_m else "AI Agent Skill",
        "body": parts[2].strip(),
    }


def compile_claude_command(skill: dict, out_dir: Path):
    cmd_dir = out_dir / ".claude" / "commands"
    cmd_dir.mkdir(parents=True, exist_ok=True)
    out_file = cmd_dir / f"{skill['name']}.md"
    content = f"""# /{skill['name']}
{skill['description']}

## Instructions
When this command is invoked:
1. Load and read the instructions from canonical skill: `.agents/skills/{skill['name']}/SKILL.md`
2. Follow all guidelines, contracts, and validation rules specified in that skill.
3. If arguments are passed ($ARGUMENTS), apply them as context parameters.
"""
    out_file.write_text(content, encoding="utf-8")
    return out_file


def compile_cursor_rule(skill: dict, out_dir: Path):
    rule_dir = out_dir / ".cursor" / "rules"
    rule_dir.mkdir(parents=True, exist_ok=True)
    out_file = rule_dir / f"{skill['name']}.mdc"
    content = f"""---
description: "{skill['description']}"
globs: ["*"]
alwaysApply: false
---

# {skill['name']} Rule
{skill['description']}

Before applying this rule, read and comply with:
- `.agents/skills/{skill['name']}/SKILL.md`
"""
    out_file.write_text(content, encoding="utf-8")
    return out_file


def compile_gemini_rule(skill: dict, out_dir: Path):
    rule_dir = out_dir / ".gemini" / "rules"
    rule_dir.mkdir(parents=True, exist_ok=True)
    out_file = rule_dir / f"{skill['name']}.md"
    content = f"""# Antigravity Rule: {skill['name']}
{skill['description']}

Trigger: Invoke when working on tasks matching: {skill['description']}
Canonical Skill Reference: `.agents/skills/{skill['name']}/SKILL.md`
"""
    out_file.write_text(content, encoding="utf-8")
    return out_file


def compile_opencode_command(skill: dict, out_dir: Path):
    cmd_dir = out_dir / ".opencode" / "commands"
    cmd_dir.mkdir(parents=True, exist_ok=True)
    out_file = cmd_dir / f"{skill['name']}.md"
    content = f"""# OpenCode Command: /{skill['name']}
{skill['description']}

Invoke instructions from: `.agents/skills/{skill['name']}/SKILL.md`
"""
    out_file.write_text(content, encoding="utf-8")
    return out_file


def compile_codex_instruction(skill: dict, out_dir: Path):
    ins_dir = out_dir / ".codex" / "instructions"
    ins_dir.mkdir(parents=True, exist_ok=True)
    out_file = ins_dir / f"{skill['name']}.md"
    content = f"""# Codex Skill Instruction: {skill['name']}
Trigger: {skill['description']}

Instructions: Read `.agents/skills/{skill['name']}/SKILL.md` and execute instructions per specification.
"""
    out_file.write_text(content, encoding="utf-8")
    return out_file


def compile_windsurf_rule(skill: dict, out_dir: Path):
    rule_dir = out_dir / ".windsurf" / "rules"
    rule_dir.mkdir(parents=True, exist_ok=True)
    out_file = rule_dir / f"{skill['name']}.md"
    content = f"""# Windsurf Rule: {skill['name']}
Description: {skill['description']}

Reference: `.agents/skills/{skill['name']}/SKILL.md`
"""
    out_file.write_text(content, encoding="utf-8")
    return out_file


def main(argv=None):
    parser = argparse.ArgumentParser(description="Multi-Host AI Agent Adapter Compiler.")
    parser.add_argument("positional_out", nargs="?", default=None, help="Legacy positional out-dir argument")
    parser.add_argument("--root", default=".", help="Repository root directory containing .agents/skills")
    parser.add_argument("--out-dir", default=None, help="Output directory for generated adapters")
    parser.add_argument("--manifest", default=None, help="Path to manifest.json")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    out_dir_str = args.out_dir or args.positional_out or "."
    out_dir = Path(out_dir_str).resolve() if not Path(out_dir_str).is_absolute() else Path(out_dir_str)

    skills_dir = root / ".agents" / "skills"
    if not skills_dir.exists():
        print(f"Error: {skills_dir} not found", file=sys.stderr)
        return 1

    count = 0
    for skill_path in sorted(skills_dir.iterdir()):
        if not skill_path.is_dir():
            continue
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            continue
        skill = parse_frontmatter(skill_md)
        if not skill:
            continue

        compile_claude_command(skill, out_dir)
        compile_cursor_rule(skill, out_dir)
        compile_gemini_rule(skill, out_dir)
        compile_opencode_command(skill, out_dir)
        compile_codex_instruction(skill, out_dir)
        compile_windsurf_rule(skill, out_dir)
        count += 1

    print(f"Compiled native adapters for {count} skills across Claude, Cursor, Gemini, OpenCode, Codex, and Windsurf.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
