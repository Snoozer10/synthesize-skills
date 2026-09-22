"""AST and pattern-based standards discovery engine. Stdlib only.

Discovers API response envelopes, error codes, naming rules, and patterns.
Caches results with SHA-256 content addressing into .runtime/standards_cache.json.
"""
import ast
import hashlib
import json
import os
import re
import sys
from pathlib import Path

IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".runtime", "dist", "build"}


def get_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    try:
        h.update(path.read_bytes())
        return h.hexdigest()
    except Exception:
        return ""


def compute_tree_sha256(root: Path) -> tuple[str, list[Path]]:
    files = []
    hasher = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file() and not any(part in IGNORE_DIRS for part in p.parts):
            if p.suffix.lower() in {".py", ".js", ".ts", ".jsx", ".tsx", ".sql", ".json"}:
                files.append(p)
                hasher.update(str(p.relative_to(root)).encode("utf-8"))
                hasher.update(get_file_sha256(p).encode("utf-8"))
    return hasher.hexdigest(), files


class PythonASTVisitor(ast.NodeVisitor):
    def __init__(self):
        self.error_codes = set()
        self.response_keys = set()
        self.db_patterns = set()

    def visit_ClassDef(self, node):
        # Look for Enum or ErrorCode classes
        is_enum = any(
            (isinstance(b, ast.Name) and "Enum" in b.id) or
            (isinstance(b, ast.Attribute) and "Enum" in b.attr)
            for b in node.bases
        ) or "Error" in node.name or "Code" in node.name

        if is_enum:
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                            if isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                                self.error_codes.add(item.value.value)
                            else:
                                self.error_codes.add(target.id)
                elif isinstance(item, ast.AnnAssign):
                    if isinstance(item.target, ast.Name) and item.target.id.isupper():
                        if item.value and isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                            self.error_codes.add(item.value.value)
                        else:
                            self.error_codes.add(item.target.id)
        self.generic_visit(node)

    def visit_Return(self, node):
        # Look for return dicts representing response envelopes
        if isinstance(node.value, ast.Dict):
            keys = set()
            for k in node.value.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    keys.add(k.value)
            if any(k in keys for k in ("data", "error", "status", "meta", "code")):
                self.response_keys.update(keys)
        self.generic_visit(node)

    def visit_Call(self, node):
        # Look for database or query calls
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        if func_name.lower() in {"execute", "query", "raw_query", "select", "fetch_one", "fetch_all"}:
            self.db_patterns.add(func_name)
        self.generic_visit(node)


def scan_python_file(path: Path) -> dict:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        visitor = PythonASTVisitor()
        visitor.visit(tree)
        return {
            "error_codes": list(visitor.error_codes),
            "response_keys": list(visitor.response_keys),
            "db_patterns": list(visitor.db_patterns)
        }
    except Exception:
        return {"error_codes": [], "response_keys": [], "db_patterns": []}


def scan_text_file(path: Path) -> dict:
    try:
        txt = path.read_text(encoding="utf-8")
    except Exception:
        return {"error_codes": [], "response_keys": [], "db_patterns": []}

    errors = set(re.findall(r"\b(ERR_[A-Z0-9_]+)\b", txt))
    status_keys = set()
    if "status" in txt and ("success" in txt or "error" in txt):
        status_keys.add("status")
    if "data" in txt and ("json.data" in txt or '"data"' in txt or "'data'" in txt):
        status_keys.add("data")
    if "error" in txt and ("json.error" in txt or '"error"' in txt or "'error'" in txt):
        status_keys.add("error")
    if "meta" in txt and ('"meta"' in txt or "'meta'" in txt):
        status_keys.add("meta")

    db = set(re.findall(r"\b(execute|query|fetch)\b", txt, re.IGNORECASE))
    return {
        "error_codes": sorted(errors),
        "response_keys": sorted(status_keys),
        "db_patterns": sorted(db)
    }


def discover_standards(root: Path, force: bool = False) -> dict:
    runtime_dir = root / ".runtime"
    cache_file = runtime_dir / "standards_cache.json"

    tree_hash, target_files = compute_tree_sha256(root)

    if not force and cache_file.is_file():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if cached.get("cache_sha256") == tree_hash:
                return cached
        except Exception:
            pass

    all_error_codes = set()
    all_response_keys = set()
    all_db_patterns = set()

    for f in target_files:
        if f.suffix.lower() == ".py":
            res = scan_python_file(f)
        else:
            res = scan_text_file(f)
        all_error_codes.update(res["error_codes"])
        all_response_keys.update(res["response_keys"])
        all_db_patterns.update(res["db_patterns"])

    # Synthesize standard response envelope
    envelope = {}
    if "status" in all_response_keys:
        envelope["status"] = "'success' | 'error'"
    if "data" in all_response_keys:
        envelope["data"] = "Payload | null"
    if "error" in all_response_keys:
        envelope["error"] = "string | ErrorDetails | null"
    if "meta" in all_response_keys:
        envelope["meta"] = "dict | null"

    standards = {
        "cache_sha256": tree_hash,
        "files_scanned": len(target_files),
        "response_envelope": envelope if envelope else {"data": "any", "status": "str"},
        "error_codes": sorted(all_error_codes),
        "database_patterns": sorted(all_db_patterns),
        "naming_conventions": {
            "functions": "snake_case (py) / camelCase (js)",
            "classes": "PascalCase",
            "constants": "UPPER_SNAKE_CASE"
        }
    }

    try:
        runtime_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(standards, indent=2), encoding="utf-8")
    except Exception:
        pass

    return standards


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Discover code and API standards via AST.")
    parser.add_argument("--dir", default=".", help="Target directory to scan")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--force", action="store_true", help="Bypass cache and force rescan")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    standards = discover_standards(root, force=args.force)

    if args.json:
        print(json.dumps(standards, indent=2))
    else:
        print(f"Standards Discovered for {root.name} (Hash: {standards['cache_sha256'][:8]}):")
        print(f"- Files Scanned: {standards['files_scanned']}")
        print(f"- Response Envelope Keys: {list(standards['response_envelope'].keys())}")
        print(f"- Error Codes: {', '.join(standards['error_codes']) or 'None'}")
        print(f"- DB Query Patterns: {', '.join(standards['database_patterns']) or 'None'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
