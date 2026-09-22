"""Spec Shaper engine. Stdlib only.

Shapes structured specifications into specs/<slug>/SPEC.md and VERIFICATION.json.
Supports non-interactive CLI flags and interactive interview mode.
"""
import argparse
import datetime
import json
import sys
from pathlib import Path


def shape_spec(
    root: Path,
    slug: str,
    title: str,
    problem: str = "",
    solution: str = "",
    criteria: list[str] = None,
    assert_files: list[str] = None,
    assert_commands: list[str] = None
) -> Path:
    criteria = criteria or []
    assert_files = assert_files or []
    assert_commands = assert_commands or []

    spec_dir = root / "specs" / slug
    spec_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.date.today().isoformat()

    spec_md_content = f"""# Specification: {title}

- **Slug:** `{slug}`
- **Date:** {date_str}
- **Status:** Draft / Active

## 1. Problem Statement
{problem or "Provide a clear description of the problem being solved."}

## 2. Proposed Solution
{solution or "High-level architectural approach and key invariants."}

## 3. Acceptance Criteria
"""
    if criteria:
        for c in criteria:
            spec_md_content += f"- [ ] {c}\n"
    else:
        spec_md_content += "- [ ] All acceptance criteria pass deterministic verification.\n"

    spec_md_content += """
## 4. Execution & Verification Boundaries
- Read-only directories must not be modified.
- Standard libraries only; zero unvetted dependencies.
- Evidence-based completion: code is complete only when `scripts/verify_spec.py` exits 0.
"""

    (spec_dir / "SPEC.md").write_text(spec_md_content, encoding="utf-8")

    verification_data = {
        "slug": slug,
        "title": title,
        "created_at": date_str,
        "assertions": {
            "files_exist": assert_files,
            "commands": assert_commands
        }
    }

    (spec_dir / "VERIFICATION.json").write_text(
        json.dumps(verification_data, indent=2), encoding="utf-8"
    )

    return spec_dir


def interactive_interview(root: Path) -> Path:
    print("=== Spec Shaper Interactive Mode ===")
    slug = input("Enter spec slug (kebab-case, e.g. user-auth): ").strip()
    title = input("Enter feature title: ").strip()
    problem = input("Enter problem description: ").strip()
    solution = input("Enter proposed solution summary: ").strip()

    print("Enter acceptance criteria (blank line to stop):")
    criteria = []
    while True:
        c = input("  - ").strip()
        if not c:
            break
        criteria.append(c)

    print("Enter required files to assert existence (blank line to stop):")
    assert_files = []
    while True:
        f = input("  file path: ").strip()
        if not f:
            break
        assert_files.append(f)

    print("Enter shell verification commands to assert exit 0 (blank line to stop):")
    assert_commands = []
    while True:
        cmd = input("  command: ").strip()
        if not cmd:
            break
        assert_commands.append(cmd)

    return shape_spec(
        root=root,
        slug=slug,
        title=title,
        problem=problem,
        solution=solution,
        criteria=criteria,
        assert_files=assert_files,
        assert_commands=assert_commands
    )


def main():
    parser = argparse.ArgumentParser(description="Shape structured specifications.")
    parser.add_argument("--dir", default=".", help="Project root directory")
    parser.add_argument("--slug", help="Spec slug (kebab-case)")
    parser.add_argument("--title", help="Human-readable feature title")
    parser.add_argument("--problem", default="", help="Problem description")
    parser.add_argument("--solution", default="", help="Proposed solution summary")
    parser.add_argument("--criterion", action="append", help="Acceptance criterion text")
    parser.add_argument("--assert-file", action="append", help="File path to assert existence")
    parser.add_argument("--assert-command", action="append", help="Command to assert exit 0")
    parser.add_argument("--interactive", action="store_true", help="Run interactive interview")
    args = parser.parse_args()

    root = Path(args.dir).resolve()

    if args.interactive:
        spec_dir = interactive_interview(root)
    else:
        if not args.slug or not args.title:
            parser.error("--slug and --title are required when not using --interactive")
        spec_dir = shape_spec(
            root=root,
            slug=args.slug,
            title=args.title,
            problem=args.problem,
            solution=args.solution,
            criteria=args.criterion,
            assert_files=args.assert_file,
            assert_commands=args.assert_command
        )

    print(f"Spec successfully shaped at: {spec_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
