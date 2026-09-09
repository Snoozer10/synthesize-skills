import argparse
import ast
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


@dataclass
class SlicedContext:
    frontmatter: str
    h1_title: str
    architecture: list[str] = field(default_factory=list)
    lexicon: list[str] = field(default_factory=list)
    invariants: list[str] = field(default_factory=list)
    cli_commands: list[str] = field(default_factory=list)
    workstreams: list[str] = field(default_factory=list)


class DependencyVisitor(ast.NodeVisitor):
    def __init__(self, root: Path, file_path: Path):
        self.root = root
        self.file_path = file_path
        self.imports = set()
        self.definitions = set()
        self.calls = set()

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.definitions.add(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.definitions.add(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.definitions.add(node.name)
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.add(node.func.attr)
        self.generic_visit(node)


def analyze_file(root: Path, file_path: Path, visited: set, depth: int = 0) -> tuple[set, set]:
    if depth > 2 or file_path in visited:
        return set(), set()

    visited.add(file_path)
    if not file_path.exists():
        return set(), set()

    try:
        content = file_path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(content, filename=str(file_path))
            visitor = DependencyVisitor(root, file_path)
            visitor.visit(tree)

            graph_files = {file_path.name}
            symbols = visitor.definitions | visitor.calls

            for imp in visitor.imports:
                parts = imp.split(".")
                possible_file = root.joinpath(*parts).with_suffix(".py")
                if possible_file.exists():
                    sub_files, sub_symbols = analyze_file(root, possible_file, visited, depth + 1)
                    graph_files.update(sub_files)
                    symbols.update(sub_symbols)

            return graph_files, symbols

        except SyntaxError:
            symbols = set(re.findall(r"(?:def|class)\s+([a-zA-Z0-9_]+)", content))
            return {file_path.name}, symbols
    except (UnicodeDecodeError, FileNotFoundError):
        pass

    return set(), set()


def slice_context(
    gemini_markdown: str, graph_files: set, symbols: set, task_desc: str
) -> SlicedContext:
    context = SlicedContext(frontmatter="", h1_title="")
    lines = gemini_markdown.split("\n")

    in_frontmatter = False
    frontmatter_lines = []
    rest_lines = []

    for i, line in enumerate(lines):
        if line.strip() == "---":
            if not in_frontmatter and i == 0:
                in_frontmatter = True
                frontmatter_lines.append(line)
            elif in_frontmatter:
                frontmatter_lines.append(line)
                in_frontmatter = False
                rest_lines = lines[i + 1 :]
                break
        elif in_frontmatter:
            frontmatter_lines.append(line)

    if not frontmatter_lines:
        rest_lines = lines
    else:
        context.frontmatter = "\n".join(frontmatter_lines)

    content = "\n".join(rest_lines)

    h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if h1_match:
        context.h1_title = h1_match.group(0)

    sections = re.split(r"^(##\s+.+)$", content, flags=re.MULTILINE)

    current_section = ""
    section_content = {}

    for part in sections:
        if part.startswith("## "):
            current_section = part
            section_content[current_section] = []
        elif current_section:
            section_content[current_section].append(part)

    for sec, parts in section_content.items():
        sec_text = sec + "".join(parts)

        if "Architecture" in sec or "Component" in sec:
            table_lines = [line for line in sec_text.split("\n") if "|" in line]
            header = table_lines[:2] if len(table_lines) >= 2 else []
            body = table_lines[2:] if len(table_lines) >= 2 else []

            filtered_body = []
            for row in body:
                if any(gf in row for gf in graph_files):
                    filtered_body.append(row)

            if filtered_body:
                context.architecture = header + filtered_body

        if "Domain Lexicon" in sec or "Ubiquitous Language" in sec:
            table_lines = [line for line in sec_text.split("\n") if "|" in line]
            header = table_lines[:2] if len(table_lines) >= 2 else []
            body = table_lines[2:] if len(table_lines) >= 2 else []

            task_lower = task_desc.lower()
            filtered_body = []
            for row in body:
                cols = row.split("|")
                if len(cols) > 1:
                    term = cols[1].strip(" `")
                    if term in symbols or term.lower() in task_lower:
                        filtered_body.append(row)

            if filtered_body:
                context.lexicon = header + filtered_body

        if "Constraints" in sec or "Invariant" in sec:
            invariants = []
            lines = sec_text.split("\n")
            for line in lines:
                if any(
                    kw in line
                    for kw in [
                        "Anti-Sycophancy",
                        "Surgical Changes",
                        "Plausibility Is Not Correctness",
                    ]
                ):
                    invariants.append(line)
                elif any(
                    kw in line.lower()
                    for kw in ["qsv", "nv12", "cdp", "whisper", "audacity", "lufs"]
                ):
                    if any(
                        kw in (task_desc.lower() + " ".join(symbols).lower())
                        for kw in ["qsv", "nv12", "cdp", "whisper", "audacity", "lufs"]
                    ):
                        invariants.append(line)
                elif line.strip().startswith("-") or line.strip().startswith("###"):
                    invariants.append(line)
            context.invariants = invariants

        if "CLI" in sec or "Workflow" in sec:
            lines = sec_text.split("\n")
            cmds = []
            has_py = any(f.endswith(".py") for f in graph_files)
            for line in lines:
                if any(kw in line for kw in ["pytest", "ruff", "mypy", "python"]):
                    if has_py:
                        cmds.append(line)
                elif line.strip().startswith("-") or line.strip().startswith("###"):
                    cmds.append(line)
            context.cli_commands = cmds

        if "Workstream" in sec or "Active" in sec:
            table_lines = [line for line in sec_text.split("\n") if "|" in line]
            header = table_lines[:2] if len(table_lines) >= 2 else []
            body = table_lines[2:] if len(table_lines) >= 2 else []
            filtered_body = []
            task_lower = task_desc.lower()
            for row in body:
                if any(word in task_lower for word in row.lower().split()):
                    filtered_body.append(row)
            if filtered_body:
                context.workstreams = header + filtered_body

    return context


def build_markdown(ctx: SlicedContext) -> str:
    parts = []
    if ctx.frontmatter:
        parts.append(ctx.frontmatter)
    if ctx.h1_title:
        parts.append(ctx.h1_title)

    if ctx.architecture:
        parts.append("## Architecture & Component Mapping")
        parts.extend(ctx.architecture)
    if ctx.lexicon:
        parts.append("### Domain Lexicon")
        parts.extend(ctx.lexicon)
    if ctx.invariants:
        parts.append("## Mandatory Engineering Constraints")
        parts.extend(ctx.invariants)
    if ctx.cli_commands:
        parts.append("## Common Workflows & CLI Commands")
        parts.extend(ctx.cli_commands)
    if ctx.workstreams:
        parts.append("## Active Workstreams")
        parts.extend(ctx.workstreams)

    return "\n".join(parts)


def clamp_budget(ctx: SlicedContext, budget: int) -> str:
    md = build_markdown(ctx)
    if len(md) // 4 <= budget:
        return md

    ctx.workstreams = []
    md = build_markdown(ctx)
    if len(md) // 4 <= budget:
        return md

    ctx.cli_commands = []
    md = build_markdown(ctx)
    if len(md) // 4 <= budget:
        return md

    ctx.architecture = []
    md = build_markdown(ctx)
    if len(md) // 4 <= budget:
        return md

    ctx.lexicon = []
    return build_markdown(ctx)


def compile_context(
    root_path: Path | str,
    files: list[str],
    task: str,
    budget: int = 600,
    context_file: Path | str = None,
    out_path: Path | str = None,
) -> tuple[str, dict]:
    root_path = Path(root_path).resolve()

    if not context_file:
        context_file = root_path / "GEMINI.md"
    else:
        context_file = Path(context_file)

    if not context_file.exists():
        gemini_md = ""
    else:
        gemini_md = context_file.read_text(encoding="utf-8")

    all_graph_files = set()
    all_symbols = set()

    visited = set()
    for f in files:
        f_path = root_path / f
        if f_path.exists():
            gf, sym = analyze_file(root_path, f_path, visited, depth=0)
            all_graph_files.update(gf)
            all_symbols.update(sym)

    ctx = slice_context(gemini_md, all_graph_files, all_symbols, task)
    final_md = clamp_budget(ctx, budget)

    metadata = {
        "budget": budget,
        "actual_tokens": len(final_md) // 4,
        "included_files": list(all_graph_files),
        "included_symbols": list(all_symbols),
    }

    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(final_md, encoding="utf-8")

    return final_md, metadata


def main():
    parser = argparse.ArgumentParser(description="JIT Context Compiler")
    parser.add_argument("--root", type=str, default=os.getcwd(), help="Repository root")
    parser.add_argument("--context-file", type=str, help="Canonical context file")
    parser.add_argument(
        "--file", dest="context_file", type=str, help="Canonical context file (alias)"
    )
    parser.add_argument("--files", type=str, required=True, help="Comma separated files")
    parser.add_argument("--task", type=str, required=True, help="Task description")
    parser.add_argument("--budget", type=int, default=600, help="Max tokens")
    parser.add_argument("--out", type=str, help="Output path")
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    files_list = [f.strip() for f in args.files.split(",")]

    md, meta = compile_context(
        root_path=args.root,
        files=files_list,
        task=args.task,
        budget=args.budget,
        context_file=args.context_file,
        out_path=args.out,
    )

    if args.json:
        payload = {"metadata": meta, "compiled_markdown": md}
        print(json.dumps(payload, indent=2))
    else:
        print(md)


if __name__ == "__main__":
    main()
