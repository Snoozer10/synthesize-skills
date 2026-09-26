"""Standards Indexer engine. Stdlib only.

Indexes symbols, error codes, response envelopes, and query methods
to their defining source files and line numbers with SHA-256 caching.
Supports reverse querying symbols and error codes via CLI and API.
"""
import argparse
import ast
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
    from discover_standards import discover_standards, compute_tree_sha256
except ImportError:
    import importlib.util
    _disc_path = _script_dir / "discover_standards.py"
    if _disc_path.is_file():
        _spec = importlib.util.spec_from_file_location("discover_standards", _disc_path)
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        discover_standards = _mod.discover_standards
        compute_tree_sha256 = _mod.compute_tree_sha256


class PythonSymbolVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str, source_lines: list[str], add_symbol, add_error_code):
        self.rel_path = rel_path
        self.source_lines = source_lines
        self.add_symbol = add_symbol
        self.add_error_code = add_error_code
        self.class_stack = []

    def _get_context(self, lineno: int, fallback: str = "") -> str:
        if 1 <= lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1].strip()
        return fallback

    def visit_ClassDef(self, node: ast.ClassDef):
        base_names = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                base_names.append(b.id)
            elif isinstance(b, ast.Attribute):
                base_names.append(b.attr)
            elif isinstance(b, ast.Subscript):
                if isinstance(b.value, ast.Name):
                    base_names.append(b.value.id)
                elif isinstance(b.value, ast.Attribute):
                    base_names.append(b.value.attr)

        is_dataclass = False
        for d in node.decorator_list:
            if isinstance(d, ast.Name) and d.id == "dataclass":
                is_dataclass = True
                break
            elif isinstance(d, ast.Call):
                if (isinstance(d.func, ast.Name) and d.func.id == "dataclass") or (
                    isinstance(d.func, ast.Attribute) and d.func.attr == "dataclass"
                ):
                    is_dataclass = True
                    break
            elif isinstance(d, ast.Attribute) and d.attr == "dataclass":
                is_dataclass = True
                break

        is_exception = any(
            b.endswith("Exception") or b.endswith("Error") or b in {"Exception", "BaseException"}
            for b in base_names
        ) or ("Error" in node.name and any("Exception" in b or "Error" in b for b in base_names))

        is_pydantic = any(
            b in {"BaseModel", "Schema"} or "Model" in b or "Schema" in b
            for b in base_names
        )

        if is_dataclass:
            kind = "dataclass"
        elif is_exception:
            kind = "exception"
        elif is_pydantic:
            kind = "pydantic_model"
        else:
            kind = "class"

        self.add_symbol(node.name, kind, self.rel_path, node.lineno)

        is_enum = any("Enum" in b for b in base_names) or "Error" in node.name or "Code" in node.name
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        target_name = target.id
                        if target_name.isupper():
                            self.add_symbol(target_name, "constant", self.rel_path, item.lineno)
                        val = None
                        if isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                            val = item.value.value
                        if val:
                            if (
                                re.match(r"^ERR_[A-Z0-9_]+$", val)
                                or re.match(r"^[A-Z0-9_]+_ERROR$", val)
                                or is_enum
                                or is_exception
                                or target_name.lower() in {"code", "default_code", "error_code", "err_code", "status_code"}
                            ):
                                ctx = self._get_context(item.lineno, f'{target_name} = "{val}"')
                                self.add_error_code(val, self.rel_path, item.lineno, ctx)
                                self.add_symbol(val, "error_code", self.rel_path, item.lineno)
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                target_name = item.target.id
                if target_name.isupper():
                    self.add_symbol(target_name, "constant", self.rel_path, item.lineno)
                val = None
                if item.value and isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                    val = item.value.value
                if val:
                    if (
                        re.match(r"^ERR_[A-Z0-9_]+$", val)
                        or re.match(r"^[A-Z0-9_]+_ERROR$", val)
                        or is_enum
                        or is_exception
                        or target_name.lower() in {"code", "default_code", "error_code", "err_code", "status_code"}
                    ):
                        ctx = self._get_context(item.lineno, f'{target_name} = "{val}"')
                        self.add_error_code(val, self.rel_path, item.lineno, ctx)
                        self.add_symbol(val, "error_code", self.rel_path, item.lineno)

        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.add_symbol(node.name, "function", self.rel_path, node.lineno)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.add_symbol(node.name, "async_function", self.rel_path, node.lineno)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        if not self.class_stack:
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    self.add_symbol(target.id, "constant", self.rel_path, node.lineno)
                    val = None
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        val = node.value.value
                    if val and (re.match(r"^ERR_[A-Z0-9_]+$", val) or re.match(r"^[A-Z0-9_]+_ERROR$", val)):
                        ctx = self._get_context(node.lineno, f'{target.id} = "{val}"')
                        self.add_error_code(val, self.rel_path, node.lineno, ctx)
                        self.add_symbol(val, "error_code", self.rel_path, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if not self.class_stack:
            if isinstance(node.target, ast.Name) and node.target.id.isupper():
                self.add_symbol(node.target.id, "constant", self.rel_path, node.lineno)
                val = None
                if node.value and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    val = node.value.value
                if val and (re.match(r"^ERR_[A-Z0-9_]+$", val) or re.match(r"^[A-Z0-9_]+_ERROR$", val)):
                    ctx = self._get_context(node.lineno, f'{node.target.id} = "{val}"')
                    self.add_error_code(val, self.rel_path, node.lineno, ctx)
                    self.add_symbol(val, "error_code", self.rel_path, node.lineno)
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, str):
            for match in re.findall(r"\b(ERR_[A-Z0-9_]+|[A-Z0-9_]+_ERROR)\b", node.value):
                lineno = getattr(node, "lineno", 1)
                ctx = self._get_context(lineno, match)
                self.add_error_code(match, self.rel_path, lineno, ctx)
                self.add_symbol(match, "error_code", self.rel_path, lineno)
        self.generic_visit(node)


def scan_python_file(path: Path, rel_path: str, add_symbol, add_error_code):
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        lines = source.splitlines()
        visitor = PythonSymbolVisitor(rel_path, lines, add_symbol, add_error_code)
        visitor.visit(tree)
    except Exception:
        pass


def scan_ts_js_file(path: Path, rel_path: str, add_symbol, add_error_code):
    try:
        source = path.read_text(encoding="utf-8")
    except Exception:
        return

    lines = source.splitlines()

    def get_lineno(char_idx: int) -> int:
        return source.count("\n", 0, char_idx) + 1

    def get_context(line_no: int, fallback: str = "") -> str:
        if 1 <= line_no <= len(lines):
            return lines[line_no - 1].strip()
        return fallback

    def repl_block(m):
        return re.sub(r"[^\n]", " ", m.group(0))

    clean_source = re.sub(r"/\*[\s\S]*?\*/", repl_block, source)
    clean_source = re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), clean_source)

    # 1. Enums
    enum_pattern = r"(?:export\s+)?(?:const\s+)?enum\s+([A-Za-z0-9_]+)\s*\{([^}]+)\}"
    for m in re.finditer(enum_pattern, clean_source):
        enum_name = m.group(1)
        line = get_lineno(m.start())
        add_symbol(enum_name, "enum", rel_path, line)
        body = m.group(2)
        body_start = m.start(2)
        for member_m in re.finditer(r'([A-Za-z0-9_]+)(?:\s*=\s*["\']([^"\']+)["\'])?', body):
            member_name = member_m.group(1)
            val = member_m.group(2)
            if not member_name:
                continue
            m_line = get_lineno(body_start + member_m.start())
            ctx = get_context(m_line, member_m.group(0).strip())
            if member_name.isupper():
                add_symbol(member_name, "constant", rel_path, m_line)
            if val:
                if (
                    re.match(r"^ERR_[A-Z0-9_]+$", val)
                    or re.match(r"^[A-Z0-9_]+_ERROR$", val)
                    or "error" in enum_name.lower()
                    or "code" in enum_name.lower()
                ):
                    add_error_code(val, rel_path, m_line, ctx)
                    add_symbol(val, "error_code", rel_path, m_line)
            elif member_name.startswith("ERR_") or member_name.endswith("_ERROR"):
                add_error_code(member_name, rel_path, m_line, ctx)
                add_symbol(member_name, "error_code", rel_path, m_line)

    # 2. Interfaces
    iface_pattern = r"(?:export\s+)?interface\s+([A-Za-z0-9_]+)"
    for m in re.finditer(iface_pattern, clean_source):
        iface_name = m.group(1)
        line = get_lineno(m.start())
        add_symbol(iface_name, "interface", rel_path, line)

    # 3. Type Aliases
    type_pattern = r"(?:export\s+)?type\s+([A-Za-z0-9_]+)(?:<[^>]*>)?\s*="
    for m in re.finditer(type_pattern, clean_source):
        type_name = m.group(1)
        line = get_lineno(m.start())
        add_symbol(type_name, "type", rel_path, line)

    # 4. Functions
    func_pattern = r"(?:export\s+)?(async\s+)?function\s+([A-Za-z0-9_]+)"
    for m in re.finditer(func_pattern, clean_source):
        is_async = bool(m.group(1))
        func_name = m.group(2)
        line = get_lineno(m.start())
        add_symbol(func_name, "async_function" if is_async else "function", rel_path, line)

    # 5. Classes
    class_pattern = r"(?:export\s+)?(?:abstract\s+)?class\s+([A-Za-z0-9_]+)"
    for m in re.finditer(class_pattern, clean_source):
        class_name = m.group(1)
        line = get_lineno(m.start())
        add_symbol(class_name, "class", rel_path, line)

    # 6. Constants
    const_pattern = r"(?:export\s+)?const\s+([A-Z][A-Z0-9_]*)\b"
    for m in re.finditer(const_pattern, clean_source):
        const_name = m.group(1)
        line = get_lineno(m.start())
        add_symbol(const_name, "constant", rel_path, line)

    # 7. Error code strings in text
    for m in re.finditer(r"\b(ERR_[A-Z0-9_]+|[A-Z0-9_]+_ERROR)\b", source):
        err_code = m.group(1)
        line = get_lineno(m.start())
        ctx = get_context(line, err_code)
        add_error_code(err_code, rel_path, line, ctx)
        add_symbol(err_code, "error_code", rel_path, line)


def build_standards_index(root: Path, force: bool = False) -> dict:
    runtime_dir = root / ".runtime"
    index_file = runtime_dir / "standards_index.json"

    tree_hash, target_files = compute_tree_sha256(root)

    if not force and index_file.is_file():
        try:
            cached = json.loads(index_file.read_text(encoding="utf-8"))
            if cached.get("cache_sha256") == tree_hash:
                return cached
        except Exception:
            pass

    standards = discover_standards(root, force=force)
    symbol_map = {}
    error_code_index = {}

    def add_symbol(name: str, kind: str, file: str, line: int):
        entry = {"name": name, "kind": kind, "file": file, "line": line}
        existing = symbol_map.setdefault(name, [])
        if not any(e["file"] == file and e["line"] == line and e["kind"] == kind for e in existing):
            existing.append(entry)

    def add_error_code(code: str, file: str, line: int, context: str):
        entry = {"error_code": code, "file": file, "line": line, "context": context}
        existing = error_code_index.setdefault(code, [])
        if not any(e["file"] == file and e["line"] == line for e in existing):
            existing.append(entry)

    for f in target_files:
        try:
            rel = f.relative_to(root).as_posix()
        except Exception:
            rel = f.as_posix()

        ext = f.suffix.lower()
        if ext == ".py":
            scan_python_file(f, rel, add_symbol, add_error_code)
        elif ext in {".ts", ".tsx", ".js", ".jsx"}:
            scan_ts_js_file(f, rel, add_symbol, add_error_code)
        elif ext in {".sql", ".json", ".md"}:
            try:
                txt = f.read_text(encoding="utf-8")
                lines = txt.splitlines()
                for m in re.finditer(r"\b(ERR_[A-Z0-9_]+|[A-Z0-9_]+_ERROR)\b", txt):
                    err_code = m.group(1)
                    line = txt.count("\n", 0, m.start()) + 1
                    ctx = lines[line - 1].strip() if 1 <= line <= len(lines) else err_code
                    add_error_code(err_code, rel, line, ctx)
                    add_symbol(err_code, "error_code", rel, line)
            except Exception:
                pass

    index_data = {
        "cache_sha256": tree_hash,
        "standards": standards,
        "symbols": symbol_map,
        "error_code_index": error_code_index,
        "indexed_files": len(target_files),
    }

    try:
        runtime_dir.mkdir(parents=True, exist_ok=True)
        index_file.write_text(json.dumps(index_data, indent=2), encoding="utf-8")
    except Exception:
        pass

    return index_data


def find_symbol_definition(index: dict, symbol_name: str) -> list[dict]:
    """Find symbol definitions matching symbol_name (case-sensitive or exact symbol match).

    Returns list of dicts: [{"name": str, "kind": str, "file": str, "line": int}]
    """
    if not isinstance(index, dict):
        return []

    symbols = index.get("symbols", {})
    if not isinstance(symbols, dict):
        if isinstance(symbols, list):
            return [e for e in symbols if isinstance(e, dict) and e.get("name") == symbol_name]
        return []

    search_name = symbol_name
    filter_kind = None
    if ":" in symbol_name:
        prefix, _, rest = symbol_name.partition(":")
        if prefix.lower() in {"def", "func", "function"}:
            search_name = rest
            filter_kind = {"function", "async_function"}
        elif prefix.lower() == "class":
            search_name = rest
            filter_kind = {"class", "pydantic_model", "dataclass", "exception"}
        elif prefix.lower() in {"interface", "type", "enum", "constant", "error_code"}:
            search_name = rest
            filter_kind = {prefix.lower()}

    # 1. Exact key match
    if search_name in symbols:
        items = symbols[search_name]
        res = list(items) if isinstance(items, list) else [items]
        if filter_kind:
            res = [r for r in res if r.get("kind") in filter_kind]
        if res:
            return res

    # 2. Iterate dict values matching name
    results = []
    for k, v in symbols.items():
        entries = v if isinstance(v, list) else [v]
        for item in entries:
            if isinstance(item, dict) and item.get("name") == search_name:
                if not filter_kind or item.get("kind") in filter_kind:
                    results.append(item)
    if results:
        return results

    # 3. Case-insensitive fallback
    lower_name = search_name.lower()
    for k, v in symbols.items():
        if k.lower() == lower_name:
            entries = v if isinstance(v, list) else [v]
            for item in entries:
                if isinstance(item, dict):
                    if not filter_kind or item.get("kind") in filter_kind:
                        results.append(item)
            if results:
                return results

    return []


def find_error_code_definition(index: dict, error_code: str) -> list[dict]:
    """Find definition locations for an error code.

    Returns list of dicts: [{"error_code": str, "file": str, "line": int, "context": str}]
    """
    if not isinstance(index, dict):
        return []

    err_index = index.get("error_code_index", {})
    if not isinstance(err_index, dict):
        return []

    # 1. Exact match in error_code_index
    if error_code in err_index:
        items = err_index[error_code]
        res = []
        for item in (items if isinstance(items, list) else [items]):
            if isinstance(item, dict):
                res.append({
                    "error_code": item.get("error_code", error_code),
                    "file": item.get("file", ""),
                    "line": item.get("line", 0),
                    "context": item.get("context", ""),
                })
        return res

    # 2. Case-insensitive match in error_code_index
    lower_code = error_code.lower()
    for k, items in err_index.items():
        if k.lower() == lower_code:
            res = []
            for item in (items if isinstance(items, list) else [items]):
                if isinstance(item, dict):
                    res.append({
                        "error_code": item.get("error_code", k),
                        "file": item.get("file", ""),
                        "line": item.get("line", 0),
                        "context": item.get("context", ""),
                    })
            return res

    # 3. Fallback: check symbols if error_code was indexed as symbol
    symbols = index.get("symbols", {})
    if isinstance(symbols, dict) and error_code in symbols:
        items = symbols[error_code]
        res = []
        for item in (items if isinstance(items, list) else [items]):
            if isinstance(item, dict) and item.get("kind") == "error_code":
                res.append({
                    "error_code": error_code,
                    "file": item.get("file", ""),
                    "line": item.get("line", 0),
                    "context": f"{item.get('name', error_code)}",
                })
        if res:
            return res

    return []


def main():
    parser = argparse.ArgumentParser(description="Index codebase standards and symbols.")
    parser.add_argument("--dir", default=".", help="Project directory to index")
    parser.add_argument("--query", default=None, help="Search for symbol definitions by name")
    parser.add_argument("--error-code", default=None, help="Search for an error code definition")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--force", action="store_true", help="Bypass cache")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    idx = build_standards_index(root, force=args.force)

    # 1. Query Symbol
    if args.query:
        matches = find_symbol_definition(idx, args.query)
        if args.json:
            print(json.dumps(matches, indent=2))
        else:
            if matches:
                print(f"Symbol '{args.query}' found ({len(matches)} definition(s)):")
                for m in matches:
                    print(f"  {m['file']}:{m['line']} [{m['kind']}] {m['name']}")
            else:
                print(f"Symbol '{args.query}' not found.")
        return 0 if matches else 1

    # 2. Query Error Code
    if args.error_code:
        matches = find_error_code_definition(idx, args.error_code)
        if args.json:
            print(json.dumps(matches, indent=2))
        else:
            if matches:
                print(f"Error code '{args.error_code}' found ({len(matches)} definition(s)):")
                for m in matches:
                    ctx = f" - {m['context']}" if m.get("context") else ""
                    print(f"  {m['file']}:{m['line']} {m['error_code']}{ctx}")
            else:
                print(f"Error code '{args.error_code}' not found.")
        return 0 if matches else 1

    # 3. Default index summary
    if args.json:
        print(json.dumps(idx, indent=2))
    else:
        print(f"Standards Index Built (Hash: {idx['cache_sha256'][:8]}):")
        print(f"- Files indexed: {idx['indexed_files']}")
        print(f"- Discovered symbols: {len(idx['symbols'])}")
        print(f"- Error codes: {len(idx.get('error_code_index', {}))}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
