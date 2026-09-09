#!/usr/bin/env python3
"""
Pre-flight Inquiry Tool for repo-blast-radius-sync.
Calculates and lists the system-wide blast radius of a target file.
Supports O(1) cached lookups and dynamic AST/Regex fallbacks.
"""

import os
import sys
import ast
import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any

class BlastRadiusResolver:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.registry_path = root_dir / ".agent" / "registry.json"
        self.registry = self._load_registry()
        
        # Regex patterns matching standard annotations
        self.doc_governs_pattern = re.compile(r"<!--\s*@governs:\s*([^\s]+?)\s*-->")
        self.code_docs_pattern = re.compile(r"@docs:\s*([^\s'\"#<>]+)")
        self.code_tests_pattern = re.compile(r"@tests:\s*([^\s'\"#<>]+)")

    def _load_registry(self) -> Dict[str, Any]:
        """Loads persistent registry from .agent/registry.json if exists."""
        if self.registry_path.exists():
            try:
                return json.loads(self.registry_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"version": "1.0.0", "files": {}}

    def parse_python_imports(self, file_path: Path) -> Set[str]:
        """Dynamically parses python imports using AST as a fallback."""
        imports: Set[str] = set()
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])
        except Exception:
            pass
        return imports

    def parse_file_annotations(self, file_path: Path) -> Dict[str, List[str]]:
        """Dynamically parses explicit annotations in a file as a fallback."""
        couplings = {"docs": [], "tests": [], "governed_by": []}
        try:
            content = file_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                markdown_match = self.doc_governs_pattern.search(line)
                if markdown_match:
                    couplings["governed_by"].append(markdown_match.group(1))
                
                doc_match = self.code_docs_pattern.search(line)
                if doc_match:
                    couplings["docs"].append(doc_match.group(1))
                
                test_match = self.code_tests_pattern.search(line)
                if test_match:
                    couplings["tests"].append(test_match.group(1))
        except Exception:
            pass
        return couplings

    def scan_workspace_dynamically(self) -> Dict[str, Any]:
        """Builds an on-the-fly ephemeral registry if cached registry is missing."""
        ephemeral_registry = {"version": "1.0.0", "files": {}, "skipped": []}
        for path in sorted(self.root_dir.glob("**/*")):
            if not path.is_file():
                continue
            rel_path = Path(path.relative_to(self.root_dir)).as_posix()
            rel_parts = Path(rel_path).parts
            if any(p.startswith(".") for p in rel_parts) or "node_modules" in rel_parts or "venv" in rel_parts or "__pycache__" in rel_parts:
                continue
            if ".agent" in rel_parts:
                continue
            if path.suffix not in {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".js", ".ts"}:
                continue
            try:
                if path.stat().st_size > 5*1024*1024:
                    ephemeral_registry["skipped"].append({"path": rel_path, "reason": "large >5MiB"}); continue
                if b"\x00" in path.read_bytes()[:8192]:
                    ephemeral_registry["skipped"].append({"path": rel_path, "reason": "binary"}); continue
            except: continue
            file_data = {"imports": [], "docs": [], "tests": [], "governed_by": []}
            try:
                if path.suffix == ".py":
                    file_data["imports"] = sorted(list(self.parse_python_imports(path)))
                annotations = self.parse_file_annotations(path)
                file_data["docs"] = sorted(list(set(annotations["docs"])))
                file_data["tests"] = sorted(list(set(annotations["tests"])))
                file_data["governed_by"] = sorted(list(set(annotations["governed_by"])))
            except UnicodeDecodeError:
                ephemeral_registry["skipped"].append({"path": rel_path, "reason": "decode"}); continue
            except: pass
            ephemeral_registry["files"][rel_path] = file_data
        return ephemeral_registry

    def resolve(self, target_file: str, symbol_filter: str = None) -> Dict[str, List[str]]:
        """Resolves full multi-dimensional blast radius for a target file."""
        from pathlib import PurePosixPath
        target_path = Path(target_file)
        rel_target = PurePosixPath(str(target_path.relative_to(self.root_dir))).as_posix() if target_path.is_absolute() else PurePosixPath(target_file).as_posix()
        
        # Determine registry context
        reg_to_use = self.registry if self.registry.get("files") else self.scan_workspace_dynamically()
        
        callers: Set[str] = set()
        docs: Set[str] = set()
        tests: Set[str] = set()
        configs: Set[str] = set()
        
        target_stem = Path(rel_target).stem
        target_config = reg_to_use.get("files", {}).get(rel_target, {})
        
        # 1. Resolve direct annotations from target
        for doc in target_config.get("docs", []):
            docs.add(doc)
        for test in target_config.get("tests", []):
            tests.add(test)
        for gov in target_config.get("governed_by", []):
            docs.add(gov)

        # 2. Map reverse dependencies (Upstream callers)
        for other_file, other_config in reg_to_use.get("files", {}).items():
            if target_stem in other_config.get("imports", []):
                callers.add(other_file)
            # Check implicit matching stems for tests or configs
            if other_file.startswith("tests/") and (target_stem in other_file or other_file.endswith(f"test_{target_stem}.py")):
                tests.add(other_file)
            if other_file.endswith((".json", ".yaml", ".toml", ".ini", ".cfg")):
                if target_stem in other_file or any(target_stem in imp for imp in other_config.get("imports", [])):
                    configs.add(other_file)

        # 3. Check markdown file governance linkages
        for other_file, other_config in reg_to_use.get("files", {}).items():
            if rel_target in other_config.get("governed_by", []):
                docs.add(other_file)

        # Apply active code parsing if a specific code symbol is targeted
        if symbol_filter:
            filtered_callers = set()
            symbol_pattern = re.compile(r"\b" + re.escape(symbol_filter) + r"\b")
            for caller in callers:
                caller_path = self.root_dir / caller
                if caller_path.exists():
                    try:
                        if symbol_pattern.search(caller_path.read_text(encoding="utf-8")):
                            filtered_callers.add(caller)
                    except Exception:
                        pass
            callers = filtered_callers

        return {
            "CODE CALLERS": sorted(list(callers)),
            "GOVERNING DOCS": sorted(list(docs)),
            "TEST SUITES": sorted(list(tests)),
            "CONFIGS/SCHEMAS": sorted(list(configs))
        }

def print_text_checklist(target_file: str, radius: Dict[str, List[str]]):
    """Outputs LLM-parseable checklist with stable leading words."""
    print("=================================================================")
    print(f"BREADTH BLAST RADIUS REPORT FOR: {target_file}")
    print("=================================================================")
    for category, files in radius.items():
        key = category.replace(" ", "_") + ":"
        print(f"\n{key}")
        if not files:
            print("  - (None detected)")
        else:
            for f in files:
                print(f"  [ ] {f}")
    print("\n=================================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query repository blast-radius for code changes", epilog="Example: python scripts/blast_radius.py src/payments/processor.py --symbol process_transaction --json")
    parser.add_argument("target", type=str, help="Relative or absolute path of target file")
    parser.add_argument("--symbol", type=str, default=None, help="Specific class or function name to trace usage")
    parser.add_argument("--json", action="store_true", help="Print structured output in JSON format")
    args = parser.parse_args()

    resolver = BlastRadiusResolver(Path(os.getcwd()))
    radius_data = resolver.resolve(args.target, symbol_filter=args.symbol)

    if args.json:
        print(json.dumps(radius_data, indent=2))
    else:
        print_text_checklist(args.target, radius_data)