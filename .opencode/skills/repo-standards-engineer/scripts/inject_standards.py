"""JIT token-bounded standards injector. Stdlib only.

Formats discovered repository standards into concise, token-bounded instructions (MIP <= 600 tokens).
Compatible with CLI stdout, @-references, and agent system prompts.
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
try:
    from discover_standards import discover_standards
except ImportError:
    from .discover_standards import discover_standards


def estimate_tokens(text: str) -> int:
    """Approximate token count (1 token ~= 4 chars or ~0.75 words)."""
    words = len(text.split())
    chars = len(text)
    return int(max(words * 1.3, chars / 3.8))


def format_standards_markdown(standards: dict, scope: str = "all", max_tokens: int = 600) -> str:
    sections = []
    sections.append("# Repository Standards & Invariants")

    # 1. Response Envelope (Priority 1)
    if scope in ("all", "api") and standards.get("response_envelope"):
        env_lines = ["## API Response Envelope:"]
        for k, v in standards["response_envelope"].items():
            env_lines.append(f"- `{k}`: {v}")
        sections.append("\n".join(env_lines))

    # 2. Error Codes (Priority 2)
    if scope in ("all", "errors") and standards.get("error_codes"):
        err_str = ", ".join(f"`{c}`" for c in standards["error_codes"][:15])
        sections.append(f"## Error Codes:\n- Standard codes: {err_str}")

    # 3. Database & Query Rules (Priority 3)
    if scope in ("all", "db") and standards.get("database_patterns"):
        db_str = ", ".join(f"`{p}`" for p in standards["database_patterns"][:10])
        sections.append(f"## DB Query Patterns:\n- Permitted methods: {db_str}")

    # 4. Naming Conventions (Priority 4)
    if scope == "all" and standards.get("naming_conventions"):
        nc_lines = ["## Naming Conventions:"]
        for k, v in standards["naming_conventions"].items():
            nc_lines.append(f"- {k}: {v}")
        sections.append("\n".join(nc_lines))

    out = "\n\n".join(sections) + "\n"

    # Enforce MIP Token Ceiling
    if estimate_tokens(out) > max_tokens:
        # Drop lowest priority sections until within limit
        while len(sections) > 2 and estimate_tokens("\n\n".join(sections) + "\n") > max_tokens:
            sections.pop()
        out = "\n\n".join(sections) + "\n"

    return out


def format_standards_compact(standards: dict, max_tokens: int = 600) -> str:
    lines = ["STANDARDS:"]
    env_keys = list(standards.get("response_envelope", {}).keys())
    if env_keys:
        lines.append(f"- Envelope keys: {', '.join(env_keys)}")
    errs = standards.get("error_codes", [])
    if errs:
        lines.append(f"- Error codes: {', '.join(errs[:8])}")
    db = standards.get("database_patterns", [])
    if db:
        lines.append(f"- DB methods: {', '.join(db[:6])}")
    out = "\n".join(lines) + "\n"
    return out


def main():
    parser = argparse.ArgumentParser(description="JIT token-bounded standards injector.")
    parser.add_argument("--dir", default=".", help="Project root directory")
    parser.add_argument("--max-tokens", type=int, default=600, help="Maximum token ceiling (MIP <= 600)")
    parser.add_argument("--scope", choices=["all", "api", "errors", "db"], default="all", help="Standards scope")
    parser.add_argument("--format", choices=["markdown", "compact", "json"], default="markdown", help="Output format")
    parser.add_argument("--at-format", action="store_true", help="Format for @-reference in context")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    standards = discover_standards(root)

    if args.format == "json":
        print(json.dumps(standards, indent=2))
        return 0

    if args.format == "compact":
        output = format_standards_compact(standards, max_tokens=args.max_tokens)
    else:
        output = format_standards_markdown(standards, scope=args.scope, max_tokens=args.max_tokens)

    if args.at_format:
        output = f"<!-- @repo-standards:begin -->\n{output}<!-- @repo-standards:end -->"

    print(output, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
