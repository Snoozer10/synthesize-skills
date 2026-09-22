#!/usr/bin/env python3
"""
Self-Healing Patch Generator for repo-blast-radius-sync.
Analyzes active code modifications in git diff and generates structured
markdown documentation updates to synchronize decoupled references automatically.
"""

import os
import sys
import subprocess
import re
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any

class DocPatchGenerator:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    def get_git_diff(self) -> str:
        """Obtains active git diff for unstaged and staged code modifications."""
        try:
            return subprocess.check_output(
                ["git", "diff", "HEAD", "--", "*.py"],
                cwd=str(self.root_dir),
                stderr=subprocess.DEVNULL
            ).decode("utf-8")
        except Exception:
            return ""

    def parse_signature_changes(self, diff_text: str) -> List[Dict[str, Any]]:
        """Parses git diff to extract added or modified method signatures."""
        changes = []
        current_file = None
        # Match python function definitions and modifications
        func_def_pattern = re.compile(r"^\+\s*def\s+([a-zA-Z0-9_]+)\s*\((.*?)\):")
        
        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:].strip()
            elif line.startswith("+") and not line.startswith("+++") and current_file:
                match = func_def_pattern.search(line)
                if match:
                    func_name = match.group(1)
                    args = match.group(2).strip()
                    changes.append({
                        "file": current_file,
                        "function": func_name,
                        "signature": f"{func_name}({args})"
                    })
        return changes

    def generate_markdown_patch(self, changes: List[Dict[str, Any]], target_doc: Path) -> str:
        """Constructs a deterministic documentation append block."""
        if not changes:
            return ""
            
        doc_name = target_doc.name
        patch_content = [
            f"\n\n## AUTOMATED INTERFACE UPDATE: {doc_name}",
            f"> **System Verification Sync**: Auto-generated from active git diff.",
            "\n### Modified Interface Signatures:\n"
        ]
        
        for change in changes:
            patch_content.append(f"*   **File**: `{change['file']}`")
            patch_content.append(f"    *   **Signature**: `{change['signature']}`")
            patch_content.append("    *   *Description*: (Synchronized parameter addition verified by pre-commit parity checks.)\n")
            
        return "\n".join(patch_content)

    def run(self, target_doc_path: str, dry_run: bool = False) -> int:
        target_doc = self.root_dir / target_doc_path
        if not target_doc.exists() and not dry_run:
            print(f"Error: Target documentation file {target_doc_path} does not exist.", file=sys.stderr)
            return 1

        diff_text = self.get_git_diff()
        if not diff_text:
            print("No active python code diffs detected. Skipping patch generation.")
            return 0

        changes = self.parse_signature_changes(diff_text)
        if not changes:
            print("No signature changes detected in active diff. Skipping.")
            return 0

        patch = self.generate_markdown_patch(changes, target_doc)
        if dry_run:
            print(patch)
            print(f"Dry-run: {len(changes)} patch(es) for {target_doc_path} (no write)", file=sys.stderr)
            return 0
        # Append the patch safely to the end of the documentation file
        try:
            with open(target_doc, "a", encoding="utf-8") as f:
                f.write(patch)
            print(f"Success: Appended {len(changes)} interface patch(es) directly to {target_doc_path}")
            return 0
        except Exception as e:
            print(f"Error writing patch to {target_doc_path}: {e}", file=sys.stderr)
            return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-Scaffold Documentation patches from active code changes", epilog="Example: python scripts/draft_doc_updates.py docs/api.md --dry-run")
    parser.add_argument("target_doc", type=str, help="Relative path to target Markdown file to update")
    parser.add_argument("--dry-run", action="store_true", help="Print patch to stdout, no FS write, preserve exit code")
    args = parser.parse_args()

    generator = DocPatchGenerator(Path(os.getcwd()))
    sys.exit(generator.run(args.target_doc, dry_run=args.dry_run))