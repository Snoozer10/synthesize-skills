#!/usr/bin/env python3
import argparse
import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from repo_indexer import index_repository
except ImportError:
    index_repository = None


@dataclass
class SignatureData:
    args: list[str]
    lineno: int
    is_async: bool


def get_staged_or_changed_files(repo_root: Path, mode: str) -> list[Path]:
    cmd = []
    if mode == "pre-commit":
        cmd = ["git", "diff", "--cached", "--name-only"]
    elif mode == "pre-push":
        try:
            subprocess.run(
                ["git", "rev-parse", "--verify", "@{u}"],
                cwd=str(repo_root),
                check=True,
                capture_output=True,
            )
            cmd = ["git", "diff", "@{u}..HEAD", "--name-only"]
        except subprocess.CalledProcessError:
            cmd = ["git", "diff", "HEAD~1..HEAD", "--name-only"]
    elif mode == "ci":
        cmd = ["git", "diff", "HEAD~1..HEAD", "--name-only"]
    elif mode == "check":
        cmd = ["git", "diff", "HEAD", "--name-only"]
    else:
        cmd = ["git", "diff", "HEAD", "--name-only"]

    try:
        res = subprocess.run(
            cmd, cwd=str(repo_root), shell=False, capture_output=True, text=True, check=True
        )
        if not res.stdout:
            return []
        paths = res.stdout.splitlines()
        valid_exts = {".py", ".ts", ".js", ".go"}
        return [repo_root / p for p in paths if p and Path(p).suffix in valid_exts]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def get_ast_signatures(content: str, filepath: Path) -> dict:
    sig = {}
    ext = filepath.suffix
    if ext == ".py":
        try:
            tree = ast.parse(content, filename=str(filepath))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.name.startswith("_"):
                        args = [arg.arg for arg in node.args.args]
                        sig[node.name] = {
                            "args": args,
                            "lineno": node.lineno,
                            "is_async": isinstance(node, ast.AsyncFunctionDef),
                        }
                elif isinstance(node, ast.ClassDef):
                    if not node.name.startswith("_"):
                        sig[node.name] = {"args": [], "lineno": node.lineno, "is_async": False}
        except SyntaxError:
            pass

    if not sig:
        for i, line in enumerate(content.splitlines(), 1):
            m = re.search(r"def\s+([a-zA-Z_]\w*)\s*\(", line)
            if m and not m.group(1).startswith("_"):
                sig[m.group(1)] = {"args": [], "lineno": i, "is_async": False}
            m = re.search(r"class\s+([a-zA-Z_]\w*)", line)
            if m and not m.group(1).startswith("_"):
                sig[m.group(1)] = {"args": [], "lineno": i, "is_async": False}

            m = re.search(r"(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_]\w*)\s*\(", line)
            if m:
                sig[m.group(1)] = {"args": [], "lineno": i, "is_async": "async" in line}
            m = re.search(r"func\s+([A-Z]\w*)\s*\(", line)
            if m:
                sig[m.group(1)] = {"args": [], "lineno": i, "is_async": False}
    return sig


def get_file_at_head(repo_root: Path, rel_path: str) -> str | None:
    rel_path_posix = str(Path(rel_path).as_posix())
    try:
        res = subprocess.run(
            ["git", "show", f"HEAD:{rel_path_posix}"],
            cwd=str(repo_root),
            shell=False,
            capture_output=True,
            check=True,
        )
        return res.stdout.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError:
        return None


def diff_signatures(old_sig: dict, new_sig: dict) -> list[str]:
    diffs = []
    for name, old_data in old_sig.items():
        if name not in new_sig:
            diffs.append(f"Removed or renamed: {name} (was at line {old_data['lineno']})")
        else:
            new_data = new_sig[name]
            if old_data["args"] != new_data["args"] and old_data["args"]:
                diffs.append(
                    f"Signature changed for {name}: {old_data['args']} -> {new_data['args']}"
                )
    return diffs


def inspect_reality_drift(repo_root: Path, gemini_content: str) -> list[str]:
    drift = []
    in_section = False
    for line in gemini_content.splitlines():
        if "## 🏗️ Architecture & Component Mapping" in line:
            in_section = True
        elif line.startswith("## ") and in_section:
            break

        if in_section and "|" in line and ".py" in line:
            m = re.search(r"\[([^\]]+\.(?:py|ts|js|go))\]", line)
            if m:
                rel_path = m.group(1)
                full_path = repo_root / rel_path
                if not full_path.exists():
                    drift.append(f"Missing referenced file from disk: {rel_path}")
    return drift


def auto_patch_gemini_md(repo_root: Path, context_file: Path) -> bool:
    if not index_repository:
        print("Error: repo_indexer module not found. Cannot auto-patch.", file=sys.stderr)
        return False

    try:
        idx = index_repository(repo_root)
        health = idx.get("architectural_health", {}).get("deep_modules", [])

        if not context_file.exists():
            return False

        content = context_file.read_text(encoding="utf-8")

        new_table = [
            "| Module / Subtree | Interface Count | Implementation LOC | Leverage | Classification |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        for h in health:
            module_path = h.get("path", "unknown")
            new_table.append(
                f"| [{module_path}]({module_path}) | {h.get('interface_count', 0)} | {h.get('loc', 0)} | {h.get('leverage', 0.0)} | Deep Module |"
            )

        table_start = -1
        table_end = -1
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "### Architectural Health & Deep Modules" in line:
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith("| Module / Subtree"):
                        table_start = j
                    elif table_start != -1 and not lines[j].startswith("|"):
                        table_end = j
                        break
                break

        if table_start != -1 and table_end != -1:
            lines = lines[:table_start] + new_table + lines[table_end:]
            content = "\n".join(lines) + "\n"

        import datetime

        now = datetime.datetime.now().strftime("%Y-%m-%d")
        content = re.sub(r'last_indexed:\s*".*"', f'last_indexed: "{now}"', content)

        context_file.write_text(content, encoding="utf-8")

        return True
    except Exception as e:
        print(f"Error auto-patching: {e}", file=sys.stderr)
        return False


def install_hooks(repo_root: Path):
    hook_path = repo_root / ".git" / "hooks" / "pre-commit"
    if not hook_path.parent.exists():
        print(f"Error: {hook_path.parent} does not exist.")
        return

    script = "#!/bin/sh\npython scripts/context_daemon.py --mode pre-commit --auto-patch\n"
    hook_path.write_text(script, encoding="utf-8")
    try:
        hook_path.chmod(0o755)
    except Exception:
        pass
    print("Installed pre-commit hook.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="VCS AST Delta Daemon")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--context-file", default="GEMINI.md", help="Context file path")
    parser.add_argument("--file", dest="context_file", help="Context file path (alias)")
    parser.add_argument(
        "--mode", choices=["pre-commit", "pre-push", "ci", "check"], default="check"
    )
    parser.add_argument("--auto-patch", action="store_true")
    parser.add_argument("--install-hooks", action="store_true")
    parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    context_file = repo_root / args.context_file

    if args.install_hooks:
        install_hooks(repo_root)
        return

    files = get_staged_or_changed_files(repo_root, args.mode)

    diagnostics = {
        "mode": args.mode,
        "files_checked": len(files),
        "signature_changes": {},
        "reality_drift": [],
    }

    for f in files:
        if not f.exists():
            continue
        rel = f.relative_to(repo_root)
        old_content = get_file_at_head(repo_root, str(rel))
        new_content = f.read_text(encoding="utf-8", errors="replace")

        old_sig = get_ast_signatures(old_content, f) if old_content else {}
        new_sig = get_ast_signatures(new_content, f)

        diffs = diff_signatures(old_sig, new_sig)
        if diffs:
            diagnostics["signature_changes"][str(rel)] = diffs

    if context_file.exists():
        gemini_content = context_file.read_text(encoding="utf-8")
        diagnostics["reality_drift"] = inspect_reality_drift(repo_root, gemini_content)

    has_errors = bool(diagnostics["signature_changes"] or diagnostics["reality_drift"])

    if args.auto_patch and has_errors:
        if auto_patch_gemini_md(repo_root, context_file):
            if args.mode == "pre-commit":
                subprocess.run(["git", "add", str(context_file)], cwd=str(repo_root), check=False)
            diagnostics["auto_patched"] = True
            has_errors = False

    if args.json:
        print(json.dumps(diagnostics, indent=2))
    else:
        if diagnostics["signature_changes"]:
            print("Signature changes detected:")
            for k, v in diagnostics["signature_changes"].items():
                print(f"  {k}:")
                for d in v:
                    print(f"    - {d}")
        if diagnostics["reality_drift"]:
            print("Reality drift detected:")
            for d in diagnostics["reality_drift"]:
                print(f"  - {d}")

        if not has_errors:
            print("No issues found.")

    if has_errors and not args.auto_patch:
        sys.exit(1)


if __name__ == "__main__":
    main()
