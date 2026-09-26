"""Standards compliance and architectural drift checker engine. Stdlib only.

Audits new/modified files or staged git diffs against repository standards:
- Rule 1: Error Code Governance (UNDECLARED_ERROR_CODE)
- Rule 2: Response Envelope Integrity (MALFORMED_RESPONSE_ENVELOPE)
- Rule 3: Database & Query Method Governance (PROHIBITED_DB_METHOD)

CLI: python scripts/check_compliance.py [--dir <path>] [--files <path> ...] [--staged] [--json]
Exits 0 on compliant, exits 1 on violations.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys

# Safe Windows console stream configuration
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
try:
    from discover_standards import discover_standards
except ImportError:
    from .discover_standards import discover_standards

IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".runtime", "dist", "build",
    ".agents", ".claude", ".gemini", ".opencode", ".codex", ".cursor", ".windsurf", ".copilot"
}

CONFLICTING_ENVELOPE_KEYS = {"result", "results", "response", "payload", "output", "body"}
PROHIBITED_DB_METHODS = {"raw_query", "execute_sql", "raw", "execute_raw", "direct_query"}


class PythonComplianceVisitor(ast.NodeVisitor):
    def __init__(self, rel_path: str, standards: dict):
        self.rel_path = rel_path
        self.standards = standards or {}
        self.allowed_error_codes = set(self.standards.get("error_codes") or [])
        self.response_envelope = self.standards.get("response_envelope") or {}
        self.database_patterns = set(self.standards.get("database_patterns") or [])

        # Parse allowed status values
        raw_status = self.response_envelope.get("status", "")
        if isinstance(raw_status, str):
            extracted = set(re.findall(r"['\"]([a-zA-Z0-9_-]+)['\"]", raw_status))
            self.allowed_status_values = extracted if extracted else {"success", "error"}
        else:
            self.allowed_status_values = {"success", "error"}

        self.violations = []
        self._seen_violations = set()

    def _add_violation(self, line: int, rule: str, message: str, details: str = ""):
        key = (line, rule, message)
        if key not in self._seen_violations:
            self._seen_violations.add(key)
            self.violations.append({
                "file": self.rel_path,
                "line": line,
                "rule": rule,
                "message": message,
                "details": details
            })

    def _format_allowed_codes(self) -> str:
        return ", ".join(sorted(self.allowed_error_codes))

    def _format_allowed_statuses(self) -> str:
        return " | ".join(repr(s) for s in sorted(self.allowed_status_values))

    # Rule 1: Error Code Governance
    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, str) and self.allowed_error_codes:
            for match in re.findall(r"\b(ERR_[A-Z0-9_]+|[A-Z0-9_]+_ERROR)\b", node.value):
                if match not in self.allowed_error_codes:
                    self._add_violation(
                        node.lineno,
                        "UNDECLARED_ERROR_CODE",
                        f"Undeclared error code '{match}'",
                        f"Allowed error codes: {self._format_allowed_codes()}"
                    )
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if self.allowed_error_codes:
            if re.match(r"^(ERR_[A-Z0-9_]+|[A-Z0-9_]+_ERROR)$", node.id):
                if node.id not in self.allowed_error_codes:
                    self._add_violation(
                        node.lineno,
                        "UNDECLARED_ERROR_CODE",
                        f"Undeclared error code '{node.id}'",
                        f"Allowed error codes: {self._format_allowed_codes()}"
                    )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if self.allowed_error_codes:
            if re.match(r"^(ERR_[A-Z0-9_]+|[A-Z0-9_]+_ERROR)$", node.attr):
                if node.attr not in self.allowed_error_codes:
                    self._add_violation(
                        node.lineno,
                        "UNDECLARED_ERROR_CODE",
                        f"Undeclared error code '{node.attr}'",
                        f"Allowed error codes: {self._format_allowed_codes()}"
                    )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        # Exception class with code assignments
        base_names = [b.id for b in node.bases if isinstance(b, ast.Name)]
        is_exc = any(b.endswith("Error") or b.endswith("Exception") or b in {"Exception", "BaseException"} for b in base_names) or ("Error" in node.name or "Exception" in node.name)
        if is_exc and self.allowed_error_codes:
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and target.id in {"code", "default_code", "error_code"}:
                            if isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                                code_val = item.value.value
                                if code_val not in self.allowed_error_codes:
                                    self._add_violation(
                                        item.lineno,
                                        "UNDECLARED_ERROR_CODE",
                                        f"Undeclared error code '{code_val}'",
                                        f"Allowed error codes: {self._format_allowed_codes()}"
                                    )
        self.generic_visit(node)

    # Rule 2: Response Envelope Integrity
    def _validate_envelope(self, keys: list[str], key_val_map: dict, lineno: int):
        if not self.response_envelope:
            return

        standard_keys = set(self.response_envelope.keys())
        has_envelope_intent = (
            any(k in standard_keys for k in keys) or
            any(k in CONFLICTING_ENVELOPE_KEYS for k in keys)
        )
        if not has_envelope_intent:
            return

        # Check for conflicting keys
        for k in keys:
            if k in CONFLICTING_ENVELOPE_KEYS and k not in standard_keys:
                self._add_violation(
                    lineno,
                    "MALFORMED_RESPONSE_ENVELOPE",
                    f"Malformed response envelope: conflicting key '{k}'",
                    f"Standard envelope keys: {', '.join(sorted(standard_keys))}"
                )

        # Check status value if present
        if "status" in key_val_map and "status" in standard_keys:
            _, v_node = key_val_map["status"]
            if isinstance(v_node, ast.Constant) and isinstance(v_node.value, str):
                if v_node.value not in self.allowed_status_values:
                    self._add_violation(
                        lineno,
                        "MALFORMED_RESPONSE_ENVELOPE",
                        f"Malformed response envelope: invalid status value '{v_node.value}'",
                        f"Standard status values: {', '.join(sorted(self.allowed_status_values))}"
                    )
            elif isinstance(v_node, ast.IfExp):
                for branch in (v_node.body, v_node.orelse):
                    if isinstance(branch, ast.Constant) and isinstance(branch.value, str):
                        if branch.value not in self.allowed_status_values:
                            self._add_violation(
                                lineno,
                                "MALFORMED_RESPONSE_ENVELOPE",
                                f"Malformed response envelope: invalid status value '{branch.value}'",
                                f"Standard status values: {', '.join(sorted(self.allowed_status_values))}"
                            )

    def visit_Return(self, node: ast.Return):
        if node.value is not None:
            if isinstance(node.value, ast.Dict):
                keys = []
                key_val_map = {}
                for k_node, v_node in zip(node.value.keys, node.value.values):
                    if isinstance(k_node, ast.Constant) and isinstance(k_node.value, str):
                        keys.append(k_node.value)
                        key_val_map[k_node.value] = (k_node, v_node)
                self._validate_envelope(keys, key_val_map, node.lineno)
            elif isinstance(node.value, ast.Call):
                keys = []
                key_val_map = {}
                for kw in node.value.keywords:
                    if kw.arg:
                        keys.append(kw.arg)
                        key_val_map[kw.arg] = (kw, kw.value)
                if keys:
                    self._validate_envelope(keys, key_val_map, node.lineno)
        self.generic_visit(node)

    # Rule 3: Database & Query Method Governance
    def visit_Call(self, node: ast.Call):
        if self.database_patterns:
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name:
                if (func_name in PROHIBITED_DB_METHODS or func_name.endswith("_raw")) and func_name not in self.database_patterns:
                    self._add_violation(
                        node.lineno,
                        "PROHIBITED_DB_METHOD",
                        f"Prohibited database query method '{func_name}'",
                        f"Allowed database query patterns: {', '.join(sorted(self.database_patterns))}"
                    )
        self.generic_visit(node)


def audit_python_file(path: Path, rel_path: str, standards: dict) -> tuple[list[dict], list[dict]]:
    violations = []
    warnings = []
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        warnings.append({"file": rel_path, "message": f"Could not read file: {e}"})
        return violations, warnings

    try:
        tree = ast.parse(content, filename=str(path))
        visitor = PythonComplianceVisitor(rel_path, standards)
        visitor.visit(tree)
        violations.extend(visitor.violations)
    except SyntaxError as e:
        warnings.append({"file": rel_path, "message": f"Python syntax error: {e}"})
        # Fallback to line scanning for syntax-error files so obvious error codes aren't lost
        allowed_error_codes = set(standards.get("error_codes") or [])
        if allowed_error_codes:
            for idx, line in enumerate(content.splitlines(), 1):
                if line.strip().startswith("#"):
                    continue
                for m in re.finditer(r"\b(ERR_[A-Z0-9_]+|[A-Z0-9_]+_ERROR)\b", line):
                    code = m.group(1)
                    if code not in allowed_error_codes:
                        violations.append({
                            "file": rel_path,
                            "line": idx,
                            "rule": "UNDECLARED_ERROR_CODE",
                            "message": f"Undeclared error code '{code}'",
                            "details": f"Allowed error codes: {', '.join(sorted(allowed_error_codes))}"
                        })

    return violations, warnings


def audit_js_ts_file(path: Path, rel_path: str, standards: dict) -> tuple[list[dict], list[dict]]:
    violations = []
    warnings = []
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        warnings.append({"file": rel_path, "message": f"Could not read file: {e}"})
        return violations, warnings

    allowed_error_codes = set(standards.get("error_codes") or [])
    response_envelope = standards.get("response_envelope") or {}
    standard_keys = set(response_envelope.keys())
    database_patterns = set(standards.get("database_patterns") or [])

    raw_status = response_envelope.get("status", "")
    if isinstance(raw_status, str):
        extracted = set(re.findall(r"['\"]([a-zA-Z0-9_-]+)['\"]", raw_status))
        allowed_status_values = extracted if extracted else {"success", "error"}
    else:
        allowed_status_values = {"success", "error"}

    lines = content.splitlines()
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(("//", "/*", "*")):
            continue

        # Rule 1: Error codes
        if allowed_error_codes:
            for m in re.finditer(r"\b(ERR_[A-Z0-9_]+|[A-Z0-9_]+_ERROR)\b", line):
                code = m.group(1)
                if code not in allowed_error_codes:
                    violations.append({
                        "file": rel_path,
                        "line": idx,
                        "rule": "UNDECLARED_ERROR_CODE",
                        "message": f"Undeclared error code '{code}'",
                        "details": f"Allowed error codes: {', '.join(sorted(allowed_error_codes))}"
                    })

        # Rule 2: Conflicting keys in response
        if response_envelope:
            for conf_key in CONFLICTING_ENVELOPE_KEYS:
                if conf_key not in standard_keys and ("data" in standard_keys or "status" in standard_keys):
                    if re.search(rf"\breturn\s+.*[\{{,]\s*[\"']?{conf_key}[\"']?\s*:", line) or re.search(rf"[\{{,]\s*[\"']?{conf_key}[\"']?\s*:", line):
                        if any(k in line for k in ("status", "error", "data", "meta")):
                            violations.append({
                                "file": rel_path,
                                "line": idx,
                                "rule": "MALFORMED_RESPONSE_ENVELOPE",
                                "message": f"Malformed response envelope: conflicting key '{conf_key}'",
                                "details": f"Standard envelope keys: {', '.join(sorted(standard_keys))}"
                            })

            m_status = re.search(r"[\"']?status[\"']?\s*:\s*[\"']([a-zA-Z0-9_-]+)[\"']", line)
            if m_status:
                status_val = m_status.group(1)
                if status_val not in allowed_status_values:
                    violations.append({
                        "file": rel_path,
                        "line": idx,
                        "rule": "MALFORMED_RESPONSE_ENVELOPE",
                        "message": f"Malformed response envelope: invalid status value '{status_val}'",
                        "details": f"Standard status values: {', '.join(sorted(allowed_status_values))}"
                    })

        # Rule 3: Prohibited DB methods
        if database_patterns:
            for prob in PROHIBITED_DB_METHODS:
                if prob not in database_patterns:
                    if re.search(rf"(\.{prob}|{prob})\s*\(", line):
                        violations.append({
                            "file": rel_path,
                            "line": idx,
                            "rule": "PROHIBITED_DB_METHOD",
                            "message": f"Prohibited database query method '{prob}'",
                            "details": f"Allowed database query patterns: {', '.join(sorted(database_patterns))}"
                        })

    return violations, warnings


def _get_staged_files(root: Path) -> list[Path]:
    try:
        res = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            cwd=str(root),
            capture_output=True,
            text=True,
            shell=False
        )
        if res.returncode == 0:
            files = []
            for line in res.stdout.splitlines():
                line = line.strip()
                if line:
                    p = root / line
                    if p.is_file() and p.suffix.lower() in {".py", ".js", ".ts", ".jsx", ".tsx"}:
                        files.append(p)
            return files
    except Exception:
        pass
    return []


def _collect_repo_files(root: Path) -> list[Path]:
    files = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            try:
                rel = p.relative_to(root)
            except ValueError:
                continue
            if not any(part in IGNORE_DIRS for part in rel.parts):
                if p.suffix.lower() in {".py", ".js", ".ts", ".jsx", ".tsx"}:
                    files.append(p)
    return files


def check_compliance(root: Path, target_files: list[Path] = None, standards: dict = None, staged: bool = False) -> tuple[bool, dict]:
    """Audits target files against discovered repository standards."""
    root = Path(root).resolve()

    # Load or discover standards
    if standards is None:
        cache_file = root / ".runtime" / "standards_cache.json"
        if cache_file.is_file():
            try:
                standards = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                standards = None
        if standards is None:
            try:
                standards = discover_standards(root)
            except Exception:
                standards = {}

    if not isinstance(standards, dict):
        standards = {}

    # Determine files to audit
    warnings = []
    if target_files is not None:
        files_to_audit = []
        for f in target_files:
            p = Path(f)
            resolved = (root / p) if not p.is_absolute() and (root / p).is_file() else p.resolve()
            if resolved.is_file():
                files_to_audit.append(resolved)
            else:
                warnings.append({"file": str(p), "message": "File not found"})
    elif staged:
        files_to_audit = _get_staged_files(root)
    else:
        files_to_audit = _collect_repo_files(root)

    violations = []
    for file_path in files_to_audit:
        try:
            rel_path = file_path.resolve().relative_to(root).as_posix()
        except ValueError:
            rel_path = file_path.as_posix()

        ext = file_path.suffix.lower()
        if ext == ".py":
            v_list, w_list = audit_python_file(file_path, rel_path, standards)
        elif ext in {".js", ".ts", ".jsx", ".tsx"}:
            v_list, w_list = audit_js_ts_file(file_path, rel_path, standards)
        else:
            v_list, w_list = [], []

        violations.extend(v_list)
        warnings.extend(w_list)

    is_compliant = len(violations) == 0
    report = {
        "compliant": is_compliant,
        "files_checked": len(files_to_audit),
        "violations_count": len(violations),
        "violations": violations,
    }
    if warnings:
        report["warnings"] = warnings

    return is_compliant, report


def main():
    parser = argparse.ArgumentParser(description="Audit files or staged diffs against repository standards.")
    parser.add_argument("--dir", default=".", help="Root directory of the repository")
    parser.add_argument("--files", nargs="*", default=None, help="Target files to check")
    parser.add_argument("--staged", action="store_true", help="Audit git staged files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    target_files = [Path(f) for f in args.files] if args.files is not None else None

    is_compliant, report = check_compliance(root, target_files=target_files, staged=args.staged)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        if is_compliant:
            print(f"COMPLIANT: Checked {report['files_checked']} file(s). 0 violations found.")
        else:
            print(f"DRIFT DETECTED: {report['violations_count']} violation(s) found across {report['files_checked']} file(s):")
            for v in report["violations"]:
                print(f"  {v['file']}:{v['line']} [{v['rule']}] {v['message']}")
                if v.get("details"):
                    print(f"    Details: {v['details']}")

    return 0 if is_compliant else 1


if __name__ == "__main__":
    sys.exit(main())
