"""Executable Verification Contract engine. Stdlib only.

Executes deterministic acceptance criteria and assertions defined in specs/<slug>/VERIFICATION.json.
Exits 0 on CONTRACT PASSED; exits 1 on CONTRACT FAILED.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


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
    commands_to_run = assertions.get("commands", [])

    results = {
        "slug": slug,
        "files_checked": len(files_to_check),
        "files_missing": [],
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

    # 1. Check file existence
    for rel_path in files_to_check:
        target = repo_root / rel_path
        if not target.exists():
            results["files_missing"].append(rel_path)

    # 2. Check commands
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

    total_assertions = len(files_to_check) + len(commands_to_run)
    if total_assertions == 0 and not allow_empty:
        passed = False
        results["status"] = "FAILED"
        results["error"] = "Contract has zero assertions. Provide assertions or pass --allow-empty."
    else:
        passed = (len(results["files_missing"]) == 0) and (len(results["command_failures"]) == 0)
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
            print(f"- Verified {receipt.get('commands_run', 0)} automated assertions passed.")
        else:
            print(f"CONTRACT FAILED: {receipt.get('slug', 'unknown')}")
            if receipt.get("files_missing"):
                print("Missing files:")
                for f in receipt["files_missing"]:
                    print(f"  [X] {f}")
            if receipt.get("command_failures"):
                print("Failed commands:")
                for fail in receipt["command_failures"]:
                    print(f"  [X] {fail['command']} (Exit code: {fail.get('exit_code')})")
                    if fail.get("stderr"):
                        print(f"      {fail['stderr']}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
