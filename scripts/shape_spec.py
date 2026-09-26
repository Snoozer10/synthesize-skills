"""Spec Shaper engine. Stdlib only.

Shapes structured specifications into specs/<slug>/SPEC.md and VERIFICATION.json.
Supports non-interactive CLI flags and interactive interview mode.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

# Safe Windows console stream configuration
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_script_dir = Path(__file__).resolve().parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))
try:
    from discover_standards import discover_standards
except ImportError:
    import importlib.util
    _disc_path = _script_dir / "discover_standards.py"
    if _disc_path.is_file():
        _spec = importlib.util.spec_from_file_location("discover_standards", _disc_path)
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        discover_standards = _mod.discover_standards


def shape_spec(
    root: Path,
    slug: str,
    title: str,
    problem: str = "",
    solution: str = "",
    criteria: list[str] = None,
    assert_files: list[str] = None,
    assert_commands: list[str] = None,
    assert_contains: list[dict] = None,
    assert_regex: list[dict] = None,
    assert_json: list[dict] = None,
    assert_symbols: list[dict] = None,
    from_standards: bool = False,
    require_envelope: bool = False,
) -> Path:
    criteria = list(criteria or [])
    assert_files = list(assert_files or [])
    assert_commands = list(assert_commands or [])
    assert_contains = list(assert_contains or [])
    assert_regex = list(assert_regex or [])
    assert_json = list(assert_json or [])
    assert_symbols = list(assert_symbols or [])

    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", slug):
        raise ValueError(f"Invalid slug '{slug}': must match ^[a-z0-9]+(-[a-z0-9]+)*$")

    envelope_keys = []
    if from_standards or require_envelope:
        standards = discover_standards(root)
        envelope = standards.get("response_envelope", {})
        if envelope:
            envelope_keys = sorted(envelope.keys()) if isinstance(envelope, dict) else sorted(envelope)
            env_crit = f"Code adheres to discovered response envelope: {', '.join(envelope_keys)}"
            if env_crit not in criteria:
                criteria.append(env_crit)

        if from_standards:
            if standards.get("error_codes"):
                err_count = len(standards["error_codes"])
                err_crit = f"Error handling adheres to declared error code standards ({err_count} declared codes)."
                if err_crit not in criteria:
                    criteria.append(err_crit)

            if standards.get("database_patterns"):
                db_str = ", ".join(sorted(standards["database_patterns"]))
                db_crit = f"Database interactions follow approved query methods: {db_str}"
                if db_crit not in criteria:
                    criteria.append(db_crit)

            comp_crit = "Passes repository standards compliance check without drift."
            if comp_crit not in criteria:
                criteria.append(comp_crit)

            if assert_files:
                comp_cmd = f"python scripts/check_compliance.py --files {' '.join(assert_files)}"
            else:
                comp_cmd = "python scripts/check_compliance.py"
            if comp_cmd not in assert_commands:
                assert_commands.append(comp_cmd)

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
    if require_envelope and envelope_keys:
        spec_md_content += f"- Discovered API response envelope adherence required: {', '.join(envelope_keys)}.\n"

    (spec_dir / "SPEC.md").write_text(spec_md_content, encoding="utf-8")

    verification_data = {
        "slug": slug,
        "title": title,
        "created_at": date_str,
        "assertions": {
            "files_exist": assert_files,
            "file_contains": assert_contains,
            "regex_matches": assert_regex,
            "json_matches": assert_json,
            "ast_symbol_present": assert_symbols,
            "commands": assert_commands
        }
    }

    (spec_dir / "VERIFICATION.json").write_text(
        json.dumps(verification_data, indent=2), encoding="utf-8"
    )

    return spec_dir


def _parse_file_colon_rest(arg: str) -> tuple[str, str]:
    """Splits <file>:<rest>, safely handling Windows drive letters like C:\\path:rest."""
    if len(arg) >= 3 and arg[1] == ":" and (arg[2] == "\\" or arg[2] == "/"):
        next_colon = arg.find(":", 2)
        if next_colon != -1:
            return arg[:next_colon], arg[next_colon + 1:]
        return arg, ""
    else:
        parts = arg.split(":", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return parts[0], ""


def interactive_interview(root: Path) -> Path:
    print("=== Spec Shaper Interactive Mode ===")
    slug = input("Enter spec slug (kebab-case, e.g. user-auth): ").strip()
    title = input("Enter feature title: ").strip()
    problem = input("Enter problem description: ").strip()
    solution = input("Enter proposed solution summary: ").strip()
    from_std_in = input("Auto-wire repository standards? (y/N): ").strip().lower()
    from_standards = from_std_in in ("y", "yes")

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
        assert_commands=assert_commands,
        from_standards=from_standards
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
    parser.add_argument("--from-standards", action="store_true", help="Auto-wire repository standards into spec")
    parser.add_argument("--require-envelope", action="store_true", help="Require response envelope adherence")
    parser.add_argument("--assert-contains", action="append", help="Assert file contains text (<file>:<text>)")
    parser.add_argument("--assert-regex", action="append", help="Assert file matches regex (<file>:<pattern>)")
    parser.add_argument("--assert-symbol", action="append", help="Assert AST symbol present (<file>:<name>[:type])")
    parser.add_argument("--assert-json", action="append", help="Assert JSON matches subset (<file>:<json_string>)")
    args = parser.parse_args()

    root = Path(args.dir).resolve()

    if args.interactive:
        spec_dir = interactive_interview(root)
    else:
        if not args.slug or not args.title:
            parser.error("--slug and --title are required when not using --interactive")

        parsed_contains = []
        if args.assert_contains:
            for item in args.assert_contains:
                f, txt = _parse_file_colon_rest(item)
                existing = next((c for c in parsed_contains if c["file"] == f), None)
                if existing:
                    existing["contains"].append(txt)
                else:
                    parsed_contains.append({"file": f, "contains": [txt]})

        parsed_regex = []
        if args.assert_regex:
            for item in args.assert_regex:
                f, pat = _parse_file_colon_rest(item)
                parsed_regex.append({"file": f, "pattern": pat})

        parsed_json = []
        if args.assert_json:
            for item in args.assert_json:
                f, j_str = _parse_file_colon_rest(item)
                parsed_json.append({"file": f, "subset": json.loads(j_str)})

        parsed_symbols = []
        if args.assert_symbol:
            for item in args.assert_symbol:
                f, rest = _parse_file_colon_rest(item)
                if ":" in rest:
                    name, sym_type = rest.split(":", 1)
                else:
                    name, sym_type = rest, "ClassDef"
                parsed_symbols.append({"file": f, "name": name, "type": sym_type or "ClassDef"})

        spec_dir = shape_spec(
            root=root,
            slug=args.slug,
            title=args.title,
            problem=args.problem,
            solution=args.solution,
            criteria=args.criterion,
            assert_files=args.assert_file,
            assert_commands=args.assert_command,
            assert_contains=parsed_contains,
            assert_regex=parsed_regex,
            assert_json=parsed_json,
            assert_symbols=parsed_symbols,
            from_standards=args.from_standards,
            require_envelope=args.require_envelope
        )

    print(f"Spec successfully shaped at: {spec_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
