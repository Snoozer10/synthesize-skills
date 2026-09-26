"""AST and pattern-based standards discovery engine. Stdlib only.

Discovers API response envelopes, error codes, naming rules, schemas, and query patterns.
Caches results with SHA-256 content addressing into .runtime/standards_cache.json.
"""
import ast
import hashlib
import json
import os
import re
import sys
from pathlib import Path

# Safe Windows console stream configuration
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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
        if p.is_file():
            rel = p.relative_to(root)
            if not any(part in IGNORE_DIRS for part in rel.parts):
                if p.suffix.lower() in {".py", ".js", ".ts", ".jsx", ".tsx", ".sql", ".json"}:
                    files.append(p)
                    hasher.update(rel.as_posix().encode("utf-8"))
                    hasher.update(get_file_sha256(p).encode("utf-8"))
    return hasher.hexdigest(), files


class PythonASTVisitor(ast.NodeVisitor):
    DB_METHODS = {
        "execute", "query", "raw_query", "select", "fetch_one", "fetch_all",
        "fetch", "find", "find_one", "find_many", "findOne", "findMany",
        "save", "create", "delete", "update", "insert", "upsert"
    }

    def __init__(self):
        self.error_codes = set()
        self.response_keys = set()
        self.db_patterns = set()
        self.schemas = {}

    def _get_base_names(self, node: ast.ClassDef) -> list[str]:
        names = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                names.append(b.id)
            elif isinstance(b, ast.Attribute):
                names.append(b.attr)
            elif isinstance(b, ast.Subscript):
                if isinstance(b.value, ast.Name):
                    names.append(b.value.id)
                elif isinstance(b.value, ast.Attribute):
                    names.append(b.value.attr)
        return names

    def _is_dataclass(self, node: ast.ClassDef) -> bool:
        for d in node.decorator_list:
            if isinstance(d, ast.Name) and d.id == "dataclass":
                return True
            elif isinstance(d, ast.Call):
                if isinstance(d.func, ast.Name) and d.func.id == "dataclass":
                    return True
                elif isinstance(d.func, ast.Attribute) and d.func.attr == "dataclass":
                    return True
            elif isinstance(d, ast.Attribute) and d.attr == "dataclass":
                return True
        return False

    def visit_ClassDef(self, node: ast.ClassDef):
        base_names = self._get_base_names(node)
        is_dataclass = self._is_dataclass(node)
        is_pydantic = any(b in {"BaseModel", "Schema"} or "Model" in b or "Schema" in b for b in base_names)
        is_typed_dict = any("TypedDict" in b for b in base_names)
        is_exception = (
            any(b.endswith("Exception") or b.endswith("Error") or b in {"Exception", "BaseException"} for b in base_names)
            or ("Error" in node.name and any("Exception" in b or "Error" in b for b in base_names))
        )
        is_enum = any("Enum" in b for b in base_names) or "Error" in node.name or "Code" in node.name

        # 1. Models & Schemas (Pydantic, Dataclasses, TypedDict)
        if is_pydantic or is_dataclass or is_typed_dict:
            fields = {}
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    type_str = "Any"
                    try:
                        type_str = ast.unparse(item.annotation)
                    except Exception:
                        pass
                    fields[item.target.id] = type_str
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            fields[target.id] = "Any"

            if fields:
                self.schemas[node.name] = fields

            is_response_name = any(sub in node.name for sub in ("Response", "Envelope", "Payload", "Result"))
            has_envelope_fields = any(f in fields for f in ("status", "data", "error", "meta", "code"))

            if is_response_name or has_envelope_fields:
                for f in fields:
                    if f in {"status", "data", "error", "meta", "code"}:
                        self.response_keys.add(f)

        # 2. Custom Exceptions & Error Hierarchies
        if is_exception:
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            target_name = target.id
                            val = None
                            if isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                                val = item.value.value
                            if val:
                                if (
                                    target_name.lower() in {"code", "default_code", "error_code", "err_code", "status_code"}
                                    or target_name.isupper()
                                    or re.match(r"^ERR_[A-Z0-9_]+$", val)
                                    or re.match(r"^[A-Z0-9_]+_ERROR$", val)
                                ):
                                    self.error_codes.add(val)
                            elif target_name.isupper() and (target_name.startswith("ERR_") or target_name.endswith("_ERROR")):
                                self.error_codes.add(target_name)
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    target_name = item.target.id
                    val = None
                    if item.value and isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                        val = item.value.value
                    if val:
                        if (
                            target_name.lower() in {"code", "default_code", "error_code", "err_code", "status_code"}
                            or target_name.isupper()
                            or re.match(r"^ERR_[A-Z0-9_]+$", val)
                            or re.match(r"^[A-Z0-9_]+_ERROR$", val)
                        ):
                            self.error_codes.add(val)
                    elif target_name.isupper() and (target_name.startswith("ERR_") or target_name.endswith("_ERROR")):
                        self.error_codes.add(target_name)

        # 3. Enum or ErrorCode classes
        if is_enum:
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            val = None
                            if isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                                val = item.value.value
                            if target.id.isupper():
                                if val:
                                    self.error_codes.add(val)
                                else:
                                    self.error_codes.add(target.id)
                            elif target.id.lower() in {"code", "default_code", "error_code"}:
                                if val:
                                    self.error_codes.add(val)
                elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    val = None
                    if item.value and isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                        val = item.value.value
                    if item.target.id.isupper():
                        if val:
                            self.error_codes.add(val)
                        else:
                            self.error_codes.add(item.target.id)
                    elif item.target.id.lower() in {"code", "default_code", "error_code"}:
                        if val:
                            self.error_codes.add(val)

        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, str):
            for match in re.findall(r"\b(ERR_[A-Z0-9_]+|[A-Z0-9_]+_ERROR)\b", node.value):
                self.error_codes.add(match)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return):
        # Dict literal returns
        if isinstance(node.value, ast.Dict):
            keys = set()
            for k in node.value.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    keys.add(k.value)
            if any(k in keys for k in ("data", "error", "status", "meta", "code")):
                self.response_keys.update(keys)
        # Call returns (e.g. Response(...), ApiResponse(...), dict(...))
        elif isinstance(node.value, ast.Call):
            call = node.value
            keys = set()
            for kw in call.keywords:
                if kw.arg:
                    keys.add(kw.arg)
            for arg in call.args:
                if isinstance(arg, ast.Dict):
                    for k in arg.keys:
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            keys.add(k.value)
            if any(k in keys for k in ("data", "error", "status", "meta", "code")):
                self.response_keys.update(keys)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        if func_name:
            if func_name in self.DB_METHODS or func_name.lower() in {m.lower() for m in self.DB_METHODS}:
                self.db_patterns.add(func_name)
        self.generic_visit(node)


def scan_python_file(path: Path) -> dict:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        visitor = PythonASTVisitor()
        visitor.visit(tree)
        return {
            "error_codes": sorted(visitor.error_codes),
            "response_keys": sorted(visitor.response_keys),
            "db_patterns": sorted(visitor.db_patterns),
            "schemas": visitor.schemas
        }
    except Exception:
        return {"error_codes": [], "response_keys": [], "db_patterns": [], "schemas": {}}


def scan_ts_file(path: Path) -> dict:
    try:
        txt = path.read_text(encoding="utf-8")
    except Exception:
        return {"error_codes": [], "response_keys": [], "db_patterns": [], "schemas": {}}

    error_codes = set(re.findall(r"\b(ERR_[A-Z0-9_]+|[A-Z0-9_]+_ERROR)\b", txt))
    response_keys = set()
    db_patterns = set()
    schemas = {}

    # 1. Enums (export enum ErrorCode { ... } or const enum ...)
    enum_pattern = r"(?:export\s+)?(?:const\s+)?enum\s+([A-Za-z0-9_]+)\s*\{([^}]+)\}"
    for m in re.finditer(enum_pattern, txt):
        enum_name, body = m.group(1), m.group(2)
        for member in re.split(r"[,;\n]", body):
            member = member.strip()
            if not member:
                continue
            m_assign = re.match(r'([A-Za-z0-9_]+)\s*=\s*["\']([^"\']+)["\']', member)
            if m_assign:
                val = m_assign.group(2)
                if re.match(r"^[A-Z0-9_]+$", val) or "error" in enum_name.lower() or "code" in enum_name.lower():
                    error_codes.add(val)
            else:
                m_id = re.match(r"([A-Za-z0-9_]+)", member)
                if m_id:
                    name = m_id.group(1)
                    if "error" in enum_name.lower() or "code" in enum_name.lower() or name.startswith("ERR_"):
                        error_codes.add(name)

    # 2. Interfaces (interface ApiResponse<T> { ... })
    iface_pattern = r"(?:export\s+)?interface\s+([A-Za-z0-9_]+)(?:<[^>]*>)?(?:\s+extends\s+[^{]+)?\s*\{([^}]+)\}"
    for m in re.finditer(iface_pattern, txt):
        iface_name, body = m.group(1), m.group(2)
        fields = re.findall(r"\b([a-zA-Z0-9_]+)\s*\??\s*:", body)
        if fields:
            schemas[iface_name] = fields
        is_response_name = any(sub in iface_name for sub in ("Response", "Envelope", "Payload", "Result"))
        has_envelope_fields = any(f in fields for f in ("status", "data", "error", "meta", "code"))
        if is_response_name or has_envelope_fields:
            for f in fields:
                if f in {"status", "data", "error", "meta", "code"}:
                    response_keys.add(f)

    # 3. Type Aliases (type ApiResponse = { ... })
    type_pattern = r"(?:export\s+)?type\s+([A-Za-z0-9_]+)(?:<[^>]*>)?\s*=\s*\{([^}]+)\}"
    for m in re.finditer(type_pattern, txt):
        type_name, body = m.group(1), m.group(2)
        fields = re.findall(r"\b([a-zA-Z0-9_]+)\s*\??\s*:", body)
        if fields:
            schemas[type_name] = fields
        is_response_name = any(sub in type_name for sub in ("Response", "Envelope", "Payload", "Result"))
        has_envelope_fields = any(f in fields for f in ("status", "data", "error", "meta", "code"))
        if is_response_name or has_envelope_fields:
            for f in fields:
                if f in {"status", "data", "error", "meta", "code"}:
                    response_keys.add(f)

    # 4. Property access and object return patterns
    if "status" in txt and ("success" in txt or "error" in txt or "json.status" in txt or '"status"' in txt or "'status'" in txt):
        response_keys.add("status")
    if "data" in txt and ("json.data" in txt or '"data"' in txt or "'data'" in txt or "res.data" in txt):
        response_keys.add("data")
    if "error" in txt and ("json.error" in txt or '"error"' in txt or "'error'" in txt or "res.error" in txt):
        response_keys.add("error")
    if "meta" in txt and ('"meta"' in txt or "'meta'" in txt or "json.meta" in txt):
        response_keys.add("meta")
    if "code" in txt and ('"code"' in txt or "'code'" in txt or "json.code" in txt):
        response_keys.add("code")

    # 5. Database query patterns (e.g. db.findMany(), repo.query(), etc.)
    for match in re.findall(r"\.(execute|query|fetch|find|findMany|findOne|save|create|delete|update|upsert)\s*\(", txt):
        db_patterns.add(match)
    for match in re.findall(r"\b(findMany|findOne|fetch_one|fetch_all|raw_query)\b", txt):
        db_patterns.add(match)

    return {
        "error_codes": sorted(error_codes),
        "response_keys": sorted(response_keys),
        "db_patterns": sorted(db_patterns),
        "schemas": schemas
    }


def scan_text_file(path: Path) -> dict:
    try:
        txt = path.read_text(encoding="utf-8")
    except Exception:
        return {"error_codes": [], "response_keys": [], "db_patterns": [], "schemas": {}}

    errors = set(re.findall(r"\b(ERR_[A-Z0-9_]+|[A-Z0-9_]+_ERROR)\b", txt))
    status_keys = set()
    if "status" in txt and ("success" in txt or "error" in txt):
        status_keys.add("status")
    if "data" in txt and ("json.data" in txt or '"data"' in txt or "'data'" in txt):
        status_keys.add("data")
    if "error" in txt and ("json.error" in txt or '"error"' in txt or "'error'" in txt):
        status_keys.add("error")
    if "meta" in txt and ('"meta"' in txt or "'meta'" in txt):
        status_keys.add("meta")
    if "code" in txt and ('"code"' in txt or "'code'" in txt):
        status_keys.add("code")

    db = set(re.findall(r"\b(execute|query|fetch|find|findMany|findOne|save|create|delete)\b", txt, re.IGNORECASE))
    return {
        "error_codes": sorted(errors),
        "response_keys": sorted(status_keys),
        "db_patterns": sorted(db),
        "schemas": {}
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
    all_schemas = {}

    for f in target_files:
        ext = f.suffix.lower()
        if ext == ".py":
            res = scan_python_file(f)
        elif ext in {".ts", ".tsx", ".js", ".jsx"}:
            res = scan_ts_file(f)
        else:
            res = scan_text_file(f)
        all_error_codes.update(res.get("error_codes", []))
        all_response_keys.update(res.get("response_keys", []))
        all_db_patterns.update(res.get("db_patterns", []))
        if "schemas" in res:
            all_schemas.update(res["schemas"])

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
    if "code" in all_response_keys:
        envelope["code"] = "int | str | null"

    standards = {
        "cache_sha256": tree_hash,
        "files_scanned": len(target_files),
        "response_envelope": envelope if envelope else {"data": "any", "status": "str"},
        "error_codes": sorted(all_error_codes),
        "database_patterns": sorted(all_db_patterns),
        "schemas": all_schemas,
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
        if standards.get("schemas"):
            print(f"- Schemas: {', '.join(standards['schemas'].keys())}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
