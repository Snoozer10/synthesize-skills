#!/usr/bin/env python3
"""
Registry Builder for repo-blast-radius-sync.
Analyzes codebase syntax structures and tags deterministically via standard AST and regex.
"""

import os
import ast
import json
import re
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Set, Any

class RegistryBuilder:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.registry_path = root_dir / ".agent" / "registry.json"
        self.registry: Dict[str, Any] = {"version": "1.0.0", "files": {}, "skipped": []}
        
        # Rigorous patterns matching standard annotations
        self.doc_governs_pattern = re.compile(r"<!--\s*@governs:\s*([^\s]+?)\s*-->")
        self.code_docs_pattern = re.compile(r"@docs:\s*([^\s'\"#<>]+)")
        self.code_tests_pattern = re.compile(r"@tests:\s*([^\s'\"#<>]+)")

    def parse_python_imports(self, file_path: Path) -> Set[str]:
        """
        Extracts import module stems using native AST structures.
        """
        imports: Set[str] = set()
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        # Extract root module stem (e.g. 'foo' from 'foo.bar')
                        stem = alias.name.split('.')[0]
                        imports.add(stem)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        stem = node.module.split('.')[0]
                        imports.add(stem)
        except Exception:
            # Fallback to skip directories, binary files, or syntax errors gracefully
            pass
        return imports

    def parse_file_annotations(self, file_path: Path) -> Dict[str, List[str]]:
        """
        Performs static scan on lines to retrieve explicit couplings.
        """
        couplings = {"docs": [], "tests": [], "governed_by": []}
        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()
            for line in lines:
                # 1. Parse markdown @governs comments
                markdown_match = self.doc_governs_pattern.search(line)
                if markdown_match:
                    couplings["governed_by"].append(markdown_match.group(1))
                
                # 2. Parse code comments or docstrings containing @docs annotations
                doc_match = self.code_docs_pattern.search(line)
                if doc_match:
                    couplings["docs"].append(doc_match.group(1))
                
                # 3. Parse code comments or docstrings containing @tests annotations
                test_match = self.code_tests_pattern.search(line)
                if test_match:
                    couplings["tests"].append(test_match.group(1))
        except Exception:
            pass
        return couplings

    def run(self):
        """
        Traverses directory, parses file signatures, and writes deterministic output.
        """
        os.makedirs(self.registry_path.parent, exist_ok=True)
        
        for path in sorted(self.root_dir.glob("**/*")):
            if not path.is_file():
                continue
            rel_path = str(path.relative_to(self.root_dir)).replace("\\", "/")
            rel_parts = Path(rel_path).parts
            # Skip build tools, virtual environments, node_modules, and metadata configurations
            if any(p.startswith(".") for p in rel_parts) or "node_modules" in rel_parts or "venv" in rel_parts or "__pycache__" in rel_parts:
                continue
            if ".agent" in rel_parts:
                continue
            if path.suffix not in {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".js", ".ts"}:
                continue
            try:
                if path.stat().st_size > 5*1024*1024:
                    self.registry["skipped"].append({"path": rel_path, "reason": "large >5MiB"})
                    print(f"WARN: skip large {rel_path}", file=sys.stderr); continue
                head = path.read_bytes()[:8192]
                if b"\x00" in head:
                    self.registry["skipped"].append({"path": rel_path, "reason": "binary"})
                    print(f"WARN: skip binary {rel_path}", file=sys.stderr); continue
            except Exception:
                continue
            # catch UnicodeDecodeError in parsers via try
            file_data = {
                "imports": [],
                "docs": [],
                "tests": [],
                "governed_by": []
            }
            try:
                if path.suffix == ".py":
                    imports = self.parse_python_imports(path)
                    file_data["imports"] = sorted(list(imports))
                annotations = self.parse_file_annotations(path)
                file_data["docs"] = sorted(list(set(annotations["docs"])))
                file_data["tests"] = sorted(list(set(annotations["tests"])))
                file_data["governed_by"] = sorted(list(set(annotations["governed_by"])))
            except UnicodeDecodeError:
                self.registry["skipped"].append({"path": rel_path, "reason": "decode error"})
                print(f"WARN: skip decode {rel_path}", file=sys.stderr); continue
            except Exception:
                pass
            self.registry["files"][rel_path] = file_data
            
        # Guarantee deterministic dictionary order on key entries
        sorted_files = {k: self.registry["files"][k] for k in sorted(self.registry["files"].keys())}
        self.registry["files"] = sorted_files
        
        # Write clean formatted JSON structure to project
        self.registry_path.write_text(json.dumps(self.registry, indent=2), encoding="utf-8")
        print(f"Registry successfully built and written to {self.registry_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deterministic Registry Builder for repo-blast-radius-sync")
    parser.add_argument("--root", type=str, default=".", help="Root repository directory to scan")
    args = parser.parse_args()
    
    root_path = Path(args.root).resolve()
    builder = RegistryBuilder(root_path)
    builder.run()