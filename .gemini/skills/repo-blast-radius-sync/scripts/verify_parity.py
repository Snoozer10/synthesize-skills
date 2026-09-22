#!/usr/bin/env python3
"""
Pre-commit Verification Gate for repo-blast-radius-sync.
Analyzes current dirty git status against compiled blast radius definitions.
Enforces strict synchronization to prevent orphaned edits.
"""

import json
import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Set, Dict, List, Any
try:
    from blast_radius import BlastRadiusResolver
except ImportError:
    from scripts.blast_radius import BlastRadiusResolver

class ParityVerifier:
    def __init__(self, root_dir: Path, strict_mode: bool = False, staged_only: bool = False, dry_run: bool = False):
        self.root_dir = root_dir
        self.resolver = BlastRadiusResolver(root_dir)
        self.strict_mode = strict_mode
        self.staged_only = staged_only
        self.dry_run = dry_run

    def get_dirty_git_files(self) -> Set[str]:
        """Obtains changed files via -z NUL parse with line-mode fallback."""
        from pathlib import PurePosixPath
        dirty_files: Set[str] = set()
        try:
            out = subprocess.check_output(
                ["git", "status", "--porcelain=v1", "-z"],
                cwd=str(self.root_dir), stderr=subprocess.DEVNULL
            )
            parts = out.split(b"\x00")
            i = 0
            while i < len(parts):
                raw = parts[i]; i += 1
                if not raw: continue
                if len(raw) < 3: continue
                xy = raw[:2]
                path = raw[3:]
                try: s = path.decode("utf-8")
                except: s = path.decode("utf-8", errors="replace")
                if s.startswith('"') and s.endswith('"'):
                    try: s = s[1:-1].encode("utf-8").decode("unicode_escape").encode("latin1").decode("utf-8", errors="replace")
                    except: pass
                if xy[0:1] in b"RC" and i < len(parts):
                    new_raw = parts[i]; i += 1
                    if new_raw:
                        try: ns = new_raw.decode("utf-8")
                        except: ns = new_raw.decode("utf-8", errors="replace")
                        if ns.startswith('"') and ns.endswith('"'):
                            try: ns = ns[1:-1].encode("utf-8").decode("unicode_escape").encode("latin1").decode("utf-8", errors="replace")
                            except: pass
                        s = ns
                ps = PurePosixPath(s).as_posix()
                staged_indicator = chr(xy[0]) if len(xy) > 0 else " "
                unstaged_indicator = chr(xy[1]) if len(xy) > 1 else " "
                if self.staged_only:
                    if staged_indicator in ("M", "A", "D", "R", "C", "T"):
                        dirty_files.add(ps)
                else:
                    if staged_indicator in ("M", "A", "D", "R", "C", "T", "?") or unstaged_indicator in ("M", "A", "D", "R", "C", "T"):
                        dirty_files.add(ps)
        except subprocess.CalledProcessError:
            try:
                out2 = subprocess.check_output(
                    ["git", "status", "--porcelain=v1"],
                    cwd=str(self.root_dir), stderr=subprocess.DEVNULL
                ).decode("utf-8", errors="replace")
                import shlex
                for line in out2.splitlines():
                    if not line.strip(): continue
                    xy = line[:2]; rest = line[3:]
                    lexer = shlex.shlex(rest, posix=True); lexer.whitespace = " "; lexer.whitespace_split = True
                    try: toks = list(lexer)
                    except: toks = [rest.strip().strip('"')]
                    s = toks[-1] if "->" in toks and len(toks) >= 3 else (toks[0] if toks else rest.strip().strip('"'))
                    ps = PurePosixPath(s).as_posix()
                    staged_indicator = xy[0] if len(xy) > 0 else " "
                    unstaged_indicator = xy[1] if len(xy) > 1 else " "
                    if self.staged_only:
                        if staged_indicator in ("M", "A", "D", "R", "C", "T"):
                            dirty_files.add(ps)
                    else:
                        if staged_indicator in ("M", "A", "D", "R", "C", "T", "?") or unstaged_indicator in ("M", "A", "D", "R", "C", "T"):
                            dirty_files.add(ps)
                print("WARN: legacy porcelain", file=sys.stderr)
            except Exception as e:
                print(f"Warning: Failed to parse git workspace state: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Failed to parse git workspace state: {e}", file=sys.stderr)
        # stale registry check
        try:
            reg = self.root_dir / ".agent" / "registry.json"
            if reg.exists():
                mtime = reg.stat().st_mtime
                max_src = max((p.stat().st_mtime for p in self.root_dir.rglob("*.py") if p.is_file()), default=mtime)
                if max_src > mtime:
                    print("ERR_STALE_REGISTRY: registry stale, run build_registry", file=sys.stderr)
        except: pass
        return {PurePosixPath(p).as_posix().replace("\\", "/") for p in dirty_files}

    def verify(self) -> int:
        """Audits dirty files vs their target blast-radius constraints."""
        dirty_files = self.get_dirty_git_files()
        if not dirty_files:
            print("Parity Verification PASSED: Git workspace is fully clean.")
            return 0

        failures: Dict[str, List[Dict[str, str]]] = {}

        for file in dirty_files:
            # Only audit code files (source code edits)
            if not file.endswith((".py", ".js", ".ts", ".go", ".cpp", ".java")):
                continue
                
            radius = self.resolver.resolve(file)
            docs_radius = set(radius["GOVERNING DOCS"])
            tests_radius = set(radius["TEST SUITES"])
            configs_radius = set(radius["CONFIGS/SCHEMAS"])
            callers_radius = set(radius["CODE CALLERS"])

            missing_docs = docs_radius - dirty_files
            missing_tests = tests_radius - dirty_files
            missing_configs = configs_radius - dirty_files
            missing_callers = callers_radius - dirty_files

            file_failures = []
            
            # Non-strict mode enforcement: coupled files defined in annotations must be touched
            if missing_docs:
                for doc in missing_docs:
                    file_failures.append({"file": doc, "type": "GOVERNING DOC", "reason": "Explicit coupling annotation"})
            if missing_tests:
                for test in missing_tests:
                    file_failures.append({"file": test, "type": "TEST SUITE", "reason": "Explicit coupling annotation"})

            # Strict mode enforcement: Caller updates and adjacent config synchronization required
            if self.strict_mode:
                if missing_configs:
                    for cfg in missing_configs:
                        file_failures.append({"file": cfg, "type": "CONFIG/SCHEMA", "reason": "Strict dependency synchronization"})
                if missing_callers:
                    for caller in missing_callers:
                        file_failures.append({"file": caller, "type": "CODE CALLER", "reason": "Strict upstream interface synchronization"})

            # Heuristic advisory (WARN, not ERR): only warn if no explicit links
            if not docs_radius:
                doc_stem_found = any(f.endswith(".md") and Path(file).stem in f for f in dirty_files)
                if not doc_stem_found and not any(f.startswith("docs/") for f in dirty_files):
                    print(f"WARN: heuristic missing docs for {file} — docs/ or .md matching {Path(file).stem}", file=sys.stderr)
            if not tests_radius:
                test_stem_found = any(f.startswith("tests/") and Path(file).stem in f for f in dirty_files)
                if not test_stem_found:
                    print(f"WARN: heuristic missing tests for {file} — tests/ matching {Path(file).stem}", file=sys.stderr)

            if file_failures:
                failures[file] = file_failures

        if failures:
            # Construct a structured, machine-readable validation failure block to stderr
            structured_error = {
                "status": "gate_failed",
                "error_code": "ERR_ORPHAN_EDIT_VIOLATION",
                "summary": "Orphaned edits detected in repository! Changes to source code files require synchronized docs/tests.",
                "payload": {
                    "dirty_files": sorted(list(dirty_files)),
                    "failures": {
                        src: [{ "file": f["file"], "type": f["type"], "coupled_via": f["reason"] } for f in flist]
                        for src, flist in failures.items()
                    }
                }
            }
            
            print("=================================================================", file=sys.stderr)
            print("CRITICAL VERIFICATION ERROR: SYSTEMIC ORPHANED EDITS", file=sys.stderr)
            print("=================================================================", file=sys.stderr)
            print(json.dumps(structured_error, indent=2), file=sys.stderr)
            print("=================================================================", file=sys.stderr)
            print("Action Required: Modify or add the missing test/documentation files listed above before completing your task.", file=sys.stderr)
            return 1

        print("Parity Verification PASSED: All blast-radius couplings are fully synchronized.")
        return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enforce synchronous repository edits across tests and documentation", epilog="Example: python scripts/verify_parity.py --strict --dry-run")
    parser.add_argument("--strict", action="store_true", help="Enforce verification across configs and upstream callers")
    parser.add_argument("--staged-only", action="store_true", help="Verify only files staged in git index")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON to stdout, preserve exit code, no FS write")
    args = parser.parse_args()

    verifier = ParityVerifier(
        Path(os.getcwd()), 
        strict_mode=args.strict, 
        staged_only=args.staged_only,
        dry_run=args.dry_run
    )
    sys.exit(verifier.verify())