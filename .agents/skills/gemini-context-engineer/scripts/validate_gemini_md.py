import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add script directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
from __version__ import __version__

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def strip_variation_selectors(text: str) -> str:
    return text.replace("\ufe0f", "")


def parse_micro_yaml(frontmatter: str) -> dict:
    frontmatter = frontmatter.lstrip("\ufeff")
    lines = frontmatter.splitlines()
    result = {}
    current_key = None

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("#"):
            continue

        # Strip inline comments
        if " #" in line_stripped:
            line_stripped = line_stripped.split(" #")[0].strip()

        if line_stripped.startswith("- "):
            if current_key:
                if not isinstance(result[current_key], list):
                    result[current_key] = [result[current_key]] if result[current_key] else []
                result[current_key].append(line_stripped[2:].strip())
        elif ":" in line_stripped:
            key, val = line_stripped.split(":", 1)
            key = key.strip()
            val = val.strip()
            current_key = key
            if val.startswith("[") and val.endswith("]"):
                # Simple JSON-style flow list
                try:
                    val = json.loads(val)
                except json.JSONDecodeError:
                    pass
            result[key] = val
    return result


def rotate_backups(filepath: Path):
    bak_pattern = f"{filepath.name}.*.bak"
    backups = sorted(filepath.parent.glob(bak_pattern))
    while len(backups) >= 3:
        oldest = backups.pop(0)
        oldest.unlink(missing_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    new_bak = filepath.parent / f"{filepath.name}.{ts}.bak"
    shutil.copy2(filepath, new_bak)


def fix_frontmatter(content: str) -> str:
    required_keys = {
        "project_name": '"Default Project"',
        "version": '"1.0.0"',
        "tech_stack": "[]",
        "rules": "[]",
        "exclude_paths": "[]",
        "last_indexed": f'"{datetime.now().isoformat()}"',
    }

    if content.startswith("---\n"):
        parts = content.split("---\n", 2)
        if len(parts) >= 3:
            frontmatter_content = parts[1]
            frontmatter_data = parse_micro_yaml(frontmatter_content)
            lines_to_add = []
            for key, default_val in required_keys.items():
                if key not in frontmatter_data:
                    lines_to_add.append(f"{key}: {default_val}")
            if lines_to_add:
                new_frontmatter = frontmatter_content
                if not new_frontmatter.endswith("\n") and new_frontmatter:
                    new_frontmatter += "\n"
                new_frontmatter += "\n".join(lines_to_add) + "\n"
                return "---\n" + new_frontmatter + "---\n" + parts[2]
            return content

    # Missing frontmatter entirely or malformed
    new_frontmatter = "".join(f"{k}: {v}\n" for k, v in required_keys.items())

    if content.startswith("---\n"):
        # Malformed (missing closing delimiter)
        return "---\n" + new_frontmatter + "---\n\n" + content[4:]

    return "---\n" + new_frontmatter + "---\n\n" + content


def validate_markdown(
    content: str, filepath: Path, repo_root: Path, federate: bool = False, reality: bool = False
):
    import graphlib

    diagnostics = {"warnings": [], "errors": [], "stats": {}}

    lines = content.splitlines()
    line_count = len(lines)
    token_count = len(content) // 4

    diagnostics["stats"]["line_count"] = line_count
    diagnostics["stats"]["token_count"] = token_count

    if line_count <= 350:
        pass
    elif line_count <= 500:
        diagnostics["warnings"].append(f"WARN_BUDGET_APPROACHING: Line count {line_count}")
    else:
        diagnostics["errors"].append(f"ERR_BUDGET_EXCEEDED: Line count {line_count} > 500")

    if token_count <= 2500:
        pass
    elif token_count <= 3500:
        diagnostics["warnings"].append(f"WARN_BUDGET_APPROACHING: Token count {token_count}")
    else:
        diagnostics["errors"].append(f"ERR_BUDGET_EXCEEDED: Token count {token_count} > 3500")

    if content.startswith("---\n"):
        parts = content.split("---\n", 2)
        if len(parts) >= 3:
            frontmatter_data = parse_micro_yaml(parts[1])
            required_keys = [
                "project_name",
                "version",
                "tech_stack",
                "rules",
                "exclude_paths",
                "last_indexed",
            ]
            for key in required_keys:
                if key not in frontmatter_data:
                    diagnostics["errors"].append(
                        f"ERR_SCHEMA_INVALID: Missing required frontmatter key '{key}'"
                    )
        else:
            diagnostics["errors"].append(
                "ERR_SCHEMA_INVALID: Missing closing frontmatter delimiter '---'"
            )
    else:
        diagnostics["errors"].append("ERR_SCHEMA_INVALID: Missing frontmatter delimiter '---'")

    h1_match = re.search(r"^# Project Context: (.*)$", content, re.MULTILINE)
    if not h1_match:
        diagnostics["errors"].append("Missing or invalid H1. Expected '# Project Context: <name>'")

    required_h2s = [
        "## 🎯 Project Overview",
        "## 🏗️ Architecture & Component Mapping",
        "## 🛑 Mandatory Engineering Constraints",
        "## 🛠️ Common Workflows & CLI Commands",
        "## 🔄 Active Workstreams & Verification Status",
    ]

    content_normalized = strip_variation_selectors(content)
    found_h2s = re.findall(r"^## (.*)$", content_normalized, re.MULTILINE)
    found_h2s = ["## " + h2.strip() for h2 in found_h2s]

    for req in required_h2s:
        if strip_variation_selectors(req) not in found_h2s:
            diagnostics["errors"].append(f"Missing required H2 section: {req}")

    if len(found_h2s) != 5:
        diagnostics["errors"].append(f"Expected exactly 5 H2 sections, found {len(found_h2s)}")

    # Link resolution
    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
    for _text, url in links:
        if url.startswith("http://") or url.startswith("https://"):
            diagnostics["warnings"].append(f"External HTTP(S) link found: {url}")
        elif url.startswith("#"):
            pass
        else:
            path = url
            if path.startswith("file://"):
                path = path.replace("file://", "", 1)
                if (
                    sys.platform == "win32"
                    and path.startswith("/")
                    and len(path) > 2
                    and path[2] == ":"
                ):
                    path = path[1:]  # e.g. /C:/Users -> C:/Users

            # Strip line anchors
            path = re.sub(r"#L\d+(?:-L\d+)?$", "", path)
            path = path.replace("\\", "/")

            try:
                target = Path(path)
                if not target.is_absolute():
                    target = repo_root / target

                if not target.exists():
                    diagnostics["errors"].append(
                        f"ERR_BROKEN_LINK: Referenced file does not exist: {url}"
                    )
            except Exception:
                diagnostics["errors"].append(
                    f"ERR_BROKEN_LINK: Referenced file does not exist: {url}"
                )

    system_excludes = {
        ".git",
        ".svn",
        "node_modules",
        "venv",
        ".venv",
        "dist",
        "build",
        "target",
        ".next",
        ".cache",
        "__pycache__",
    }
    architecture_section_text = ""
    in_arch = False
    for line in lines:
        if line.strip() == "## 🏗️ Architecture & Component Mapping":
            in_arch = True
        elif line.startswith("## ") and in_arch:
            in_arch = False
        if in_arch:
            architecture_section_text += line + "\n"

    import os

    try:
        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [d for d in dirs if d not in system_excludes]
            if Path(root) != repo_root and "GEMINI.md" in files:
                rel_path = str(Path(root).relative_to(repo_root) / "GEMINI.md").replace("\\", "/")
                if rel_path not in architecture_section_text and rel_path not in content:
                    diagnostics["warnings"].append(
                        f"WARN_CHILD_INDEX_INCOMPLETE: Nested GEMINI.md at '{rel_path}' not indexed in Section 2"
                    )
    except Exception:
        pass

    if reality:
        arch_links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", architecture_section_text)
        for _text, url in arch_links:
            if not (url.startswith("http://") or url.startswith("https://") or url.startswith("#")):
                path = url
                if path.startswith("file://"):
                    path = path.replace("file://", "", 1)
                    if (
                        sys.platform == "win32"
                        and path.startswith("/")
                        and len(path) > 2
                        and path[2] == ":"
                    ):
                        path = path[1:]
                path = re.sub(r"#L\d+(?:-L\d+)?$", "", path)
                path = path.replace("\\", "/")
                try:
                    target = Path(path)
                    if not target.is_absolute():
                        target = repo_root / target
                    if not target.exists():
                        diagnostics["warnings"].append(
                            f"WARN_REALITY_DRIFT: Documented component does not exist on disk: '{url}'"
                        )
                except Exception:
                    pass

    if "### Domain Lexicon & Ubiquitous Language" in architecture_section_text:
        lexicon_lines = architecture_section_text.split("### Domain Lexicon & Ubiquitous Language")[
            1
        ]
        lexicon_text = re.split(r"\n##?#? ", lexicon_lines)[0]
        has_table = False
        for line in lexicon_text.splitlines():
            if "|" in line:
                headers = [h.strip().lower() for h in line.split("|")]
                if "term" in headers and "canonical meaning" in headers:
                    has_table = True
                    break
        if not has_table:
            diagnostics["errors"].append(
                "ERR_LEXICON_MISSING_TABLE: Domain Lexicon section must contain a table with 'Term' and 'Canonical Meaning' headers"
            )

    section_5_text = ""
    in_sec_5 = False
    for line in lines:
        clean_line = strip_variation_selectors(line).strip()
        if clean_line == "## 🔄 Active Workstreams & Verification Status":
            in_sec_5 = True
        elif line.startswith("## ") and in_sec_5:
            if clean_line != "## 🔄 Active Workstreams & Verification Status":
                in_sec_5 = False
        if in_sec_5:
            section_5_text += line + "\n"

    graph = {}
    table_lines = [
        line
        for line in section_5_text.splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    if table_lines:
        headers = [h.strip().lower() for h in table_lines[0].strip().strip("|").split("|")]
        if "id" in headers and "blocked by" in headers:
            id_idx = headers.index("id")
            blocked_idx = headers.index("blocked by")
            for row in table_lines[2:]:
                cols = [c.strip() for c in row.strip().strip("|").split("|")]
                if len(cols) > max(id_idx, blocked_idx):
                    task_id = cols[id_idx]
                    blocked_by = cols[blocked_idx]
                    if task_id and task_id != "-":
                        deps = [
                            d.strip()
                            for d in blocked_by.split(",")
                            if d.strip() and d.strip() != "-"
                        ]
                        graph[task_id] = set(deps)

    for line in section_5_text.splitlines():
        m = re.search(r"\|\s*(?:\[)?(#\d+)(?:\])?\s*\|", line)
        if not m:
            m = re.search(r"\[(#\d+)\]", line)
        if m:
            task_id = m.group(1)
            blocked_m = re.search(r"Blocked [bB]y:\s*([#\d\s,]+)", line)
            deps = []
            if blocked_m:
                deps = [
                    d.strip()
                    for d in blocked_m.group(1).split(",")
                    if d.strip() and d.strip() != "-"
                ]
            if task_id not in graph:
                graph[task_id] = set(deps)

    if graph:
        try:
            ts = graphlib.TopologicalSorter(graph)
            ts.prepare()
        except graphlib.CycleError as e:
            cycle = e.args[1] if len(e.args) > 1 else str(e)
            diagnostics["errors"].append(
                f"ERR_DAG_CYCLE: Circular dependency detected in workstreams: {cycle}"
            )

    for fname in ("CLAUDE.md", "AGENTS.md"):
        fpath = repo_root / fname
        status = "missing"
        if fpath.is_symlink():
            status = "symlink"
        elif fpath.exists():
            try:
                f_content = fpath.read_text(encoding="utf-8")
                if "<!-- AGENT-SYNC: GEMINI.md -->" in f_content or "GEMINI.md" in f_content:
                    status = "pointer_shim"
                else:
                    status = "divergent"
            except Exception:
                status = "divergent"

        if status == "divergent":
            diagnostics["warnings"].append(
                f"WARN_SPLIT_BRAIN_CONTEXT: '{fname}' exists and diverges from GEMINI.md. Run with --federate to align."
            )

        if federate and status in ("divergent", "missing"):
            try:
                if fpath.exists():
                    fpath.unlink()
                os.symlink("GEMINI.md", fpath)
                if status == "divergent":
                    diagnostics["warnings"] = [
                        w
                        for w in diagnostics["warnings"]
                        if not w.startswith(f"WARN_SPLIT_BRAIN_CONTEXT: '{fname}'")
                    ]
            except OSError:
                shim = "<!-- AGENT-SYNC: GEMINI.md -->\n# Synced Context\nThis repository uses [GEMINI.md](./GEMINI.md) as the authoritative context file. Please refer to GEMINI.md for all project instructions, architecture, and constraints.\n"
                fpath.write_text(shim, encoding="utf-8")
                if status == "divergent":
                    diagnostics["warnings"] = [
                        w
                        for w in diagnostics["warnings"]
                        if not w.startswith(f"WARN_SPLIT_BRAIN_CONTEXT: '{fname}'")
                    ]

    return diagnostics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path", nargs="?", default="GEMINI.md", help="Path to markdown file")
    parser.add_argument("--context-file", dest="context_file", help="Path to markdown file (alias)")
    parser.add_argument("--file", dest="context_file", help="Path to markdown file (alias)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--strict", action="store_true", help="Warnings treated as errors")
    parser.add_argument("--fix-frontmatter", action="store_true", help="Fix frontmatter")
    parser.add_argument("--backup", action="store_true", help="Create rotating backup")
    parser.add_argument("--federate", action="store_true", help="Align cross-ecosystem manifests")
    parser.add_argument("--reality", action="store_true", help="Enable reality drift validation")
    parser.add_argument("--version", action="version", version=__version__)

    args = parser.parse_args()

    filepath = Path(args.context_file if args.context_file else args.file_path).resolve()

    if not filepath.exists():
        err = {"error": f"File not found: {filepath}"}
        if args.json:
            print(json.dumps(err))
        else:
            print(err["error"])
        sys.exit(1)

    if args.backup:
        rotate_backups(filepath)

    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        err = {"error": f"Failed to read file: {e}"}
        if args.json:
            print(json.dumps(err))
        else:
            print(err["error"])
        sys.exit(1)

    if args.fix_frontmatter:
        fixed_content = fix_frontmatter(content)
        if fixed_content != content:
            content = fixed_content
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

    repo_root = filepath.parent
    diagnostics = validate_markdown(content, filepath, repo_root, args.federate, args.reality)

    has_errors = len(diagnostics["errors"]) > 0
    has_warnings = len(diagnostics["warnings"]) > 0

    exit_code = 1 if has_errors or (args.strict and has_warnings) else 0

    if args.json:
        print(json.dumps(diagnostics, indent=2))
    else:
        print(f"Validation for {filepath.name}:")
        print(f"Stats: {diagnostics['stats']}")
        if has_errors:
            print("Errors:")
            for e in diagnostics["errors"]:
                print(f"  - {e}")
        if has_warnings:
            print("Warnings:")
            for w in diagnostics["warnings"]:
                print(f"  - {w}")
        if not has_errors and not has_warnings:
            print("All checks passed!")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
