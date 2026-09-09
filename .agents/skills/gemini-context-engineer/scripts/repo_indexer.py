import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import tomllib

# Add script directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
from __version__ import __version__

SYSTEM_EXCLUDES = {
    ".git", ".svn", "node_modules", "venv", ".venv", "dist", "build", "target",
    ".next", ".cache", "__pycache__"
}

def is_dangerous_root(target: Path) -> bool:
    target = target.resolve()
    try:
        if target == Path.home():
            return True
        if target == target.anchor or str(target) == os.path.abspath(os.sep):
            return True
    except Exception:
        pass
    return False

def run_git_ls_files(root: Path):
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=True
        )
        return [root / f for f in result.stdout.splitlines() if f]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def fallback_walk(root: Path, max_depth: int):
    files = []
    root = root.resolve()

    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        try:
            depth = len(current.relative_to(root).parts)
        except ValueError:
            depth = 0

        if depth > max_depth:
            dirnames.clear()
            continue

        dirnames[:] = [d for d in dirnames if d not in SYSTEM_EXCLUDES]

        for f in filenames:
            files.append(current / f)

    return files

def parse_node(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return {
                "name": data.get("name"),
                "version": data.get("version"),
                "dependencies": list(data.get("dependencies", {}).keys()),
                "devDependencies": list(data.get("devDependencies", {}).keys()),
                "scripts": list(data.get("scripts", {}).keys()),
                "workspaces": data.get("workspaces")
            }
    except Exception:
        return {}

def parse_python_toml(path: Path) -> dict:
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
            return {
                "project": data.get("project", {}),
                "poetry": data.get("tool", {}).get("poetry", {}),
                "ruff": data.get("tool", {}).get("ruff", {}),
                "pytest": data.get("tool", {}).get("pytest", {})
            }
    except Exception:
        return {}

def parse_rust_toml(path: Path) -> dict:
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
            return {
                "package": data.get("package", {}),
                "dependencies": list(data.get("dependencies", {}).keys()),
                "workspace": data.get("workspace", {})
            }
    except Exception:
        return {}

def parse_go_mod(path: Path) -> dict:
    res = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("module "):
                    res["module"] = line.split(" ")[1]
                elif line.startswith("go "):
                    res["go_version"] = line.split(" ")[1]
    except Exception:
        pass
    return res

def parse_manifests(files: list, root: Path) -> dict:
    manifests = {}
    for f in files:
        if f.name == "package.json":
            manifests["node"] = parse_node(f)
        elif f.name == "pyproject.toml":
            manifests["python"] = parse_python_toml(f)
        elif f.name == "Cargo.toml":
            manifests["rust"] = parse_rust_toml(f)
        elif f.name == "go.mod":
            manifests["go"] = parse_go_mod(f)
    return manifests


def analyze_leverage(filepath: Path):
    name = filepath.name.lower()
    parts = [p.lower() for p in filepath.parts]
    if (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.ts")
        or name.endswith(".spec.ts")
        or name.endswith("_test.go")
        or name in ("conftest.py", "setup.py")
        or any(p in ("tests", ".tests", "testing", "fixtures", "mocks") for p in parts)
    ):
        return None

    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return None

    ext = filepath.suffix
    interface_count = 0

    if ext == ".py":
        try:
            tree = ast.parse(content)
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.name.startswith('_'):
                        interface_count += 1 + len(node.args.args) + len(node.args.kwonlyargs)
                elif isinstance(node, ast.ClassDef):
                    if not node.name.startswith('_'):
                        interface_count += 1
                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith('_'):
                                interface_count += 1 + len(item.args.args) + len(item.args.kwonlyargs)
            loc = sum(1 for line in content.splitlines() if line.strip() and not line.strip().startswith('#'))
        except (SyntaxError, UnicodeDecodeError, ValueError):
            return None
    elif ext in (".js", ".ts", ".jsx", ".tsx", ".go"):
        loc = sum(1 for line in content.splitlines() if line.strip() and not line.strip().startswith('//'))
        if ext in (".js", ".ts", ".jsx", ".tsx"):
            interface_count += len(re.findall(r'\bexport\s+(?:function|class|const|let|var)\s+([a-zA-Z0-9_]+)', content))
            interface_count += len(re.findall(r'\bexport\s*\{\s*[^}]+\s*\}', content))
        else: # .go
            interface_count += len(re.findall(r'\bfunc\s+([A-Z][a-zA-Z0-9_]*)', content))
            interface_count += len(re.findall(r'\btype\s+([A-Z][a-zA-Z0-9_]*)\s+(?:struct|interface)', content))
    else:
        return None

    leverage = round(loc / max(1, interface_count), 2)
    return {"path": str(filepath), "leverage": leverage, "interface_count": interface_count, "loc": loc}

def index_repository(root_path: Path | str, max_depth: int = 3, scope: str = None, federate: bool = False, shard: str = None, grill: bool = False) -> dict:
    target_root = Path(root_path).resolve()
    if scope != "project" and is_dangerous_root(target_root):
        raise ValueError("Dangerous root directory detected. Use --scope project to override.")

    start_time = time.time()

    files = run_git_ls_files(target_root)
    traversal = "git"
    if files is None:
        files = fallback_walk(target_root, max_depth)
        traversal = "walk"

    manifests = parse_manifests(files, target_root)

    deep_modules = []
    shallow_modules = []

    for f in files:
        if f.suffix in (".py", ".js", ".ts", ".jsx", ".tsx", ".go"):
            res = analyze_leverage(f)
            if res:
                if res["leverage"] >= 8.0:
                    deep_modules.append(res)
                elif res["leverage"] < 2.5 and res["interface_count"] >= 3:
                    shallow_modules.append(res)

    deep_modules.sort(key=lambda x: x["leverage"], reverse=True)
    shallow_modules.sort(key=lambda x: x["leverage"])

    architectural_health = {
        "deep_modules": deep_modules[:5],
        "shallow_modules": shallow_modules[:5]
    }

    frontier_questions = []
    if grill:
        gemini_md_exists = (target_root / "GEMINI.md").exists()
        claude_md_exists = (target_root / "CLAUDE.md").exists()
        if not gemini_md_exists and not claude_md_exists:
            frontier_questions.append("Missing invariant documentation. What is the canonical system context?")
        if not files:
            frontier_questions.append("Empty repository detected. Where is the source code?")

    if shard:
        shard_path = target_root / shard
        shard_path.mkdir(parents=True, exist_ok=True)
        shard_gemini = shard_path / "GEMINI.md"
        if not shard_gemini.exists():
            shard_gemini.write_text("---\nproject_name: \"Child Component\"\nversion: \"1.0.0\"\ntech_stack: []\nrules: []\nexclude_paths: []\nlast_indexed: \"\"\n---\n\n# Project Context: Child Component\n\n## 🎯 Project Overview\n\n## 🏗️ Architecture & Component Mapping\n\n## 🛑 Mandatory Engineering Constraints\n\n## 🛠️ Common Workflows & CLI Commands\n\n## 🔄 Active Workstreams & Verification Status\n", encoding="utf-8")

    child_contexts = []
    try:
        for p in fallback_walk(target_root, max_depth):
            if p.name == "GEMINI.md" and p != target_root / "GEMINI.md":
                child_contexts.append({"path": str(p.relative_to(target_root)).replace("\\", "/"), "scope": p.parent.name})
    except Exception:
        pass

    federation = {}
    for fname in ("CLAUDE.md", "AGENTS.md", ".cursorrules"):
        fpath = target_root / fname
        if not fpath.exists():
            status = "missing"
        elif fpath.is_symlink():
            status = "symlink"
        else:
            try:
                content = fpath.read_text(encoding="utf-8")
                if "<!-- AGENT-SYNC: GEMINI.md -->" in content or "GEMINI.md" in content:
                    status = "pointer_shim"
                else:
                    status = "divergent"
            except Exception:
                status = "divergent"

        federation[fname] = status

        if federate and status in ("missing", "divergent"):
            try:
                if fpath.exists():
                    fpath.unlink()
                os.symlink("GEMINI.md", fpath)
                federation[fname] = "symlink"
            except OSError:
                shim = "<!-- AGENT-SYNC: GEMINI.md -->\n# Synced Context\nThis repository uses [GEMINI.md](./GEMINI.md) as the authoritative context file. Please refer to GEMINI.md for all project instructions, architecture, and constraints.\n"
                fpath.write_text(shim, encoding="utf-8")
                federation[fname] = "pointer_shim"

    elapsed = (time.time() - start_time) * 1000

    res_dict = {
        "root": str(target_root),
        "file_count": len(files),
        "traversal_engine": traversal,
        "manifests": manifests,
        "architectural_health": architectural_health,
        "child_contexts": child_contexts,
        "federation": federation,
        "elapsed_ms": round(elapsed, 2)
    }
    if grill:
        res_dict["frontier_questions"] = frontier_questions
    return res_dict

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Root directory")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--max-depth", type=int, default=3, help="Max depth for fallback walk")
    parser.add_argument("--scope", choices=["project", "global"], default=None, help="Safety scope")
    parser.add_argument("--federate", action="store_true", help="Align cross-ecosystem manifests")
    parser.add_argument("--shard", type=str, default=None, help="Create scoped child GEMINI.md in subdir")
    parser.add_argument("--grill", action="store_true", help="Include frontier questions for context discovery")
    parser.add_argument("--version", action="version", version=__version__)

    args = parser.parse_args()

    try:
        result = index_repository(args.root, args.max_depth, args.scope, args.federate, args.shard, args.grill)
    except ValueError as e:
        err = {"error": str(e)}
        if args.json:
            print(json.dumps(err))
        else:
            print(err["error"])
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Root: {result['root']}")
        print(f"Files: {result['file_count']} (Engine: {result['traversal_engine']})")
        print(f"Manifests found: {list(result['manifests'].keys())}")
        print(f"Child Contexts: {len(result['child_contexts'])}")
        print(f"Time: {result['elapsed_ms']}ms")

if __name__ == "__main__":
    main()
