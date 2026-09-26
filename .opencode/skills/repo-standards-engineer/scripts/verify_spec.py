"""Executable Verification Contract engine. Stdlib only.

Executes deterministic acceptance criteria and assertions defined in specs/<slug>/VERIFICATION.json.
Exits 0 on CONTRACT PASSED; exits 1 on CONTRACT FAILED.
"""
import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _is_json_subset(expected, actual) -> tuple[bool, str]:
    """Recursively check if expected is a subset of actual JSON structure."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False, f"Expected dict, got {type(actual).__name__}"
        for k, exp_val in expected.items():
            if k not in actual:
                return False, f"Missing key '{k}' in JSON object"
            ok, reason = _is_json_subset(exp_val, actual[k])
            if not ok:
                return False, f"At key '{k}': {reason}"
        return True, ""
    elif isinstance(expected, list):
        if not isinstance(actual, list):
            return False, f"Expected list, got {type(actual).__name__}"
        for exp_item in expected:
            found = False
            for act_item in actual:
                ok, _ = _is_json_subset(exp_item, act_item)
                if ok:
                    found = True
                    break
            if not found:
                return False, f"Expected list element {json.dumps(exp_item)} not found in actual list"
        return True, ""
    else:
        if expected != actual:
            return False, f"Expected {json.dumps(expected)!r}, got {json.dumps(actual)!r}"
        return True, ""


def _check_ast_symbol(content: str, name: str, sym_type: str) -> tuple[bool, str]:
    """Check if Python content contains an AST symbol of given name and type."""
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        return False, f"Python syntax error: {e}"

    target_type = sym_type.lower()
    for node in ast.walk(tree):
        if target_type == "class":
            if isinstance(node, ast.ClassDef) and node.name == name:
                return True, ""
        elif target_type == "function":
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
                return True, ""
        elif target_type == "variable":
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == name:
                        return True, ""
                    elif isinstance(target, (ast.Tuple, ast.List)):
                        for elt in target.elts:
                            if isinstance(elt, ast.Name) and elt.id == name:
                                return True, ""
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.target.id == name:
                    return True, ""
        else:
            return False, f"Unsupported symbol type '{sym_type}' (expected 'class', 'function', or 'variable')"

    return False, f"Symbol '{name}' of type '{sym_type}' not found"


def verify_spec(spec_dir: Path, json_output: bool = False, repo_root: Path = None, allow_empty: bool = False) -> tuple[bool, dict]:
    v_file = spec_dir / "VERIFICATION.json"
    if not v_file.is_file():
        return False, {"slug": spec_dir.name, "status": "FAILED", "error": f"Missing required contract definition: {v_file}"}

    try:
        config = json.loads(v_file.read_text(encoding="utf-8"))
    except Exception as e:
        return False, {"slug": spec_dir.name, "status": "FAILED", "error": f"Failed to parse VERIFICATION.json: {e}"}

    slug = config.get("slug", spec_dir.name)
    assertions = config.get("assertions", {})

    files_to_check = assertions.get("files_exist", [])
    file_contains = assertions.get("file_contains", [])
    regex_matches = assertions.get("regex_matches", [])
    json_matches = assertions.get("json_matches", [])
    ast_symbol_present = assertions.get("ast_symbol_present", [])
    commands_to_run = assertions.get("commands", [])

    semantic_count = len(file_contains) + len(regex_matches) + len(json_matches) + len(ast_symbol_present)

    results = {
        "slug": slug,
        "files_checked": len(files_to_check),
        "files_missing": [],
        "assertions_checked": semantic_count,
        "assertion_failures": [],
        "commands_run": len(commands_to_run),
        "command_failures": []
    }

    if not repo_root:
        cur = spec_dir.resolve()
        found_root = None
        for _ in range(10):
            if (cur / ".git").exists() or (cur / "VERSION").exists():
                found_root = cur
                break
            if cur.parent == cur:
                break
            cur = cur.parent
        if found_root:
            repo_root = found_root
        elif len(spec_dir.resolve().parents) >= 2 and spec_dir.resolve().parent.name == "specs":
            repo_root = spec_dir.resolve().parents[1]
        else:
            repo_root = Path.cwd()

    def _resolve_file(file_path: str) -> Path:
        p = Path(file_path)
        return p if p.is_absolute() else (repo_root / p)

    # 1. Check file existence
    for rel_path in files_to_check:
        target = _resolve_file(rel_path)
        if not target.exists():
            results["files_missing"].append(rel_path)

    # 2. Check file_contains
    for item in file_contains:
        rel_path = item.get("file", "")
        expected_substrings = item.get("contains", [])
        target = _resolve_file(rel_path)
        if not target.is_file():
            results["assertion_failures"].append({
                "type": "file_contains",
                "file": rel_path,
                "reason": f"File does not exist: {rel_path}"
            })
            continue

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            results["assertion_failures"].append({
                "type": "file_contains",
                "file": rel_path,
                "reason": f"Failed to read file: {e}"
            })
            continue

        missing = [sub for sub in expected_substrings if sub not in content]
        if missing:
            results["assertion_failures"].append({
                "type": "file_contains",
                "file": rel_path,
                "reason": f"Missing expected substring(s): {missing}"
            })

    # 3. Check regex_matches
    for item in regex_matches:
        rel_path = item.get("file", "")
        pattern = item.get("pattern", "")
        target = _resolve_file(rel_path)
        if not target.is_file():
            results["assertion_failures"].append({
                "type": "regex_matches",
                "file": rel_path,
                "reason": f"File does not exist: {rel_path}"
            })
            continue

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            results["assertion_failures"].append({
                "type": "regex_matches",
                "file": rel_path,
                "reason": f"Failed to read file: {e}"
            })
            continue

        try:
            matched = bool(re.search(pattern, content, re.MULTILINE | re.DOTALL))
        except re.error as e:
            results["assertion_failures"].append({
                "type": "regex_matches",
                "file": rel_path,
                "reason": f"Invalid regex pattern '{pattern}': {e}"
            })
            continue

        if not matched:
            results["assertion_failures"].append({
                "type": "regex_matches",
                "file": rel_path,
                "reason": f"Pattern '{pattern}' did not match content"
            })

    # 4. Check json_matches
    for item in json_matches:
        rel_path = item.get("file", "")
        subset = item.get("subset", {})
        target = _resolve_file(rel_path)
        if not target.is_file():
            results["assertion_failures"].append({
                "type": "json_matches",
                "file": rel_path,
                "reason": f"File does not exist: {rel_path}"
            })
            continue

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            actual_json = json.loads(content)
        except Exception as e:
            results["assertion_failures"].append({
                "type": "json_matches",
                "file": rel_path,
                "reason": f"Invalid JSON in {rel_path}: {e}"
            })
            continue

        matches, reason = _is_json_subset(subset, actual_json)
        if not matches:
            results["assertion_failures"].append({
                "type": "json_matches",
                "file": rel_path,
                "reason": reason
            })

    # 5. Check ast_symbol_present
    for item in ast_symbol_present:
        rel_path = item.get("file", "")
        name = item.get("name", "")
        sym_type = item.get("type", "")
        target = _resolve_file(rel_path)
        if not target.is_file():
            results["assertion_failures"].append({
                "type": "ast_symbol_present",
                "file": rel_path,
                "reason": f"File does not exist: {rel_path}"
            })
            continue

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            results["assertion_failures"].append({
                "type": "ast_symbol_present",
                "file": rel_path,
                "reason": f"Failed to read file: {e}"
            })
            continue

        present, reason = _check_ast_symbol(content, name, sym_type)
        if not present:
            results["assertion_failures"].append({
                "type": "ast_symbol_present",
                "file": rel_path,
                "reason": reason
            })

    # 6. Check commands
    for cmd in commands_to_run:
        try:
            res = subprocess.run(
                cmd,
                shell=True,
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60
            )
            if res.returncode != 0:
                results["command_failures"].append({
                    "command": cmd,
                    "exit_code": res.returncode,
                    "stderr": res.stderr.strip(),
                    "stdout": res.stdout.strip()
                })
        except Exception as e:
            results["command_failures"].append({
                "command": cmd,
                "error": str(e)
            })

    total_assertions = len(files_to_check) + semantic_count + len(commands_to_run)
    if total_assertions == 0 and not allow_empty:
        passed = False
        results["status"] = "FAILED"
        results["error"] = "Contract has zero assertions. Provide assertions or pass --allow-empty."
    else:
        passed = (
            len(results["files_missing"]) == 0
            and len(results["assertion_failures"]) == 0
            and len(results["command_failures"]) == 0
        )
        results["status"] = "PASSED" if passed else "FAILED"

    return passed, results


def main():
    parser = argparse.ArgumentParser(description="Verify executable spec contract.")
    parser.add_argument("--spec", required=True, help="Path to spec directory (e.g. specs/user-auth)")
    parser.add_argument("--root", default=None, help="Root directory for file/command assertions")
    parser.add_argument("--allow-empty", action="store_true", help="Allow specs with zero assertions to pass")
    parser.add_argument("--json", action="store_true", help="Output JSON receipt")
    args = parser.parse_args()

    spec_dir = Path(args.spec).resolve()
    repo_root = Path(args.root).resolve() if args.root else None
    passed, receipt = verify_spec(spec_dir, json_output=args.json, repo_root=repo_root, allow_empty=args.allow_empty)

    if args.json:
        print(json.dumps(receipt, indent=2))
    else:
        if passed:
            print(f"CONTRACT PASSED: {receipt['slug']}")
            print(f"- Verified {receipt.get('files_checked', 0)} files present.")
            if receipt.get("assertions_checked", 0) > 0:
                print(f"- Verified {receipt.get('assertions_checked', 0)} semantic assertions passed.")
            print(f"- Verified {receipt.get('commands_run', 0)} automated assertions passed.")
        else:
            print(f"CONTRACT FAILED: {receipt.get('slug', 'unknown')}")
            if receipt.get("error"):
                print(f"  Error: {receipt['error']}")
            if receipt.get("files_missing"):
                print("Missing files:")
                for f in receipt["files_missing"]:
                    print(f"  [X] {f}")
            if receipt.get("assertion_failures"):
                print("Assertion failures:")
                for fail in receipt["assertion_failures"]:
                    print(f"  [X] [{fail.get('type')}] {fail.get('file')}: {fail.get('reason')}")
            if receipt.get("command_failures"):
                print("Failed commands:")
                for fail in receipt["command_failures"]:
                    print(f"  [X] {fail['command']} (Exit code: {fail.get('exit_code')})")
                    if fail.get("stderr"):
                        print(f"      {fail['stderr']}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
