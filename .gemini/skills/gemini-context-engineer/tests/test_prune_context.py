import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

# Add script directory to sys.path
SCRIPT_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR.resolve()))

try:
    from prune_context import (
        prune_gemini_md,
        prune_continuity_md,
        format_metrics_table,
        rotate_backups,
        atomic_write_text,
    )
except ImportError:
    # Expected during TDD red phase before prune_context.py is created
    prune_gemini_md = None
    prune_continuity_md = None
    format_metrics_table = None
    rotate_backups = None
    atomic_write_text = None


SAMPLE_GEMINI_MD = """---
project_name: "test-pipeline"
version: "1.0.0"
tech_stack:
  - "python"
rules:
  - "stdlib-only"
exclude_paths:
  - ".git"
last_indexed: "2026-01-01"
generator: "gemini-context-engineer/v4.0.0"
---

# Project Context: test-pipeline

## 🎯 Project Overview
This is a test project overview description.

## Adaptive multi-channel production: current opt-in contract
- Subprocess arguments MUST always be passed as a list with shell=False.
- File-backed FFmpeg filter graphs use `-/filter_complex`; `-filter_complex_script` is removed in FFmpeg 9 and must not re-enter either render path.
- No DNS, network-adapter or system network configuration changes are part of this workflow.
- Regular informational sentence describing channel profiles.

## 🏗️ Architecture & Component Mapping
```text
Component A -> Component B
```

| Domain | Package | Entrypoint | Key Responsibility |
| :--- | :--- | :--- | :--- |
| Audio | audio/ | generate.py | Audio generation |

### Domain Lexicon & Ubiquitous Language
| Term | Canonical Meaning | Forbidden Synonyms |
| :--- | :--- | :--- |
| `Timeline` | SSOT | "Word list" |

## 🛑 Mandatory Engineering Constraints

### Technical & Environmental Invariants
- **Existing Rule**: Always use UTF-8.

## 🛠️ Common Workflows & CLI Commands
- Run tests: `python -m unittest`

## 🔄 Active Workstreams & Verification Status
| ID | Workstream Slice | Status | Blocked By | Proof Command |
| :--- | :--- | :--- | :--- | :--- |
| `#1` | Audio DSP | Done | - | `pytest` |
| `#2` | Video Pipeline | In Progress | `#1` | `pytest` |
| `#3` | Docs Sync | Done | `#2` | `pytest` |

### Known Failure Modes & Project Learnings
- [LEARNING-001]: Learning 1 description.
- [LEARNING-002]: Learning 2 description.
- [LEARNING-003]: Learning 3 description.
- [LEARNING-004]: Learning 4 description.
- [LEARNING-005]: Learning 5 description.
- [LEARNING-006]: Learning 6 description.
- [LEARNING-007]: Learning 7 description.
- [LEARNING-008]: Learning 8 description.
- [LEARNING-009]: Learning 9 description.
"""


SAMPLE_CONTINUITY_MD = """- Goal (incl. success criteria): Complete context pruning engine.
- Constraints/Assumptions:
  - Stdlib-only Python.
  - Windows console UTF-8.
- Key decisions:
  - Shard rogue H2s to docs/specs.
- State:
  - Done:
    - Task 1: Non-destructive federation.
- Historical Archive:
    1. Milestone 1: Initial prototype designed.
    2. Milestone 2: Basic tests written.
    3. Milestone 3: Benchmark suite established.
    4. Milestone 4: Docker setup completed.
    5. Milestone 5: CI workflow verified.
  - Now: Task 2 implementation.
  - Next: Task 3 pressure verification.
- Open questions: None.
- Working set (files/ids/commands): scripts/prune_context.py, tests/test_prune_context.py
"""


class TestPruneContext(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.repo_root = Path(self.temp_dir)
        (self.repo_root / "docs").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_imports_available(self):
        """Assert prune_context module functions are imported."""
        self.assertIsNotNone(prune_gemini_md, "prune_gemini_md must be implemented")
        self.assertIsNotNone(prune_continuity_md, "prune_continuity_md must be implemented")
        self.assertIsNotNone(format_metrics_table, "format_metrics_table must be implemented")

    def test_prune_gemini_rogue_h2_extraction(self):
        """Verifies rogue H2 is moved to docs/specs/ and invariants preserved in Section 3."""
        pruned_content, result = prune_gemini_md(SAMPLE_GEMINI_MD, self.repo_root, keep_learnings=7)

        # 1. Rogue section H2 must NOT exist in pruned GEMINI.md
        self.assertNotIn("## Adaptive multi-channel production", pruned_content)

        # 2. Canonical 5 H2 headers must all be present
        canonical_h2s = [
            "## 🎯 Project Overview",
            "## 🏗️ Architecture & Component Mapping",
            "## 🛑 Mandatory Engineering Constraints",
            "## 🛠️ Common Workflows & CLI Commands",
            "## 🔄 Active Workstreams & Verification Status",
        ]
        for h2 in canonical_h2s:
            self.assertIn(h2, pruned_content)

        # Count H2 headers: must be exactly 5
        h2_headers = [line for line in pruned_content.splitlines() if line.startswith("## ")]
        self.assertEqual(len(h2_headers), 5, f"Expected exactly 5 H2s, found: {h2_headers}")

        # 3. Sharded file must exist under docs/specs/
        specs_dir = self.repo_root / "docs" / "specs"
        self.assertTrue(specs_dir.exists())
        spec_files = list(specs_dir.glob("*.md"))
        self.assertTrue(len(spec_files) >= 1)
        sharded_file = spec_files[0]
        sharded_text = sharded_file.read_text(encoding="utf-8")
        self.assertIn("Subprocess arguments", sharded_text)

        # 4. Pointer note must be present in pruned GEMINI.md
        rel_spec_path = str(sharded_file.relative_to(self.repo_root)).replace("\\", "/")
        self.assertIn(f"[{rel_spec_path}]({rel_spec_path})", pruned_content)
        self.assertIn("> [!NOTE]", pruned_content)

        # 5. Invariants must be preserved in Section 3 under Technical & Environmental Invariants
        self.assertIn("### Technical & Environmental Invariants", pruned_content)
        self.assertTrue(
            "filter_complex" in pruned_content or "-/filter_complex" in pruned_content,
            "filter_complex invariant must be preserved in Section 3",
        )
        self.assertTrue(
            "No DNS" in pruned_content or "no dns" in pruned_content.lower(),
            "No DNS invariant must be preserved in Section 3",
        )
        self.assertTrue(
            "MUST" in pruned_content or "Subprocess" in pruned_content,
            "Subprocess MUST invariant must be preserved in Section 3",
        )

        # 6. Frontmatter last_indexed must be updated to current date
        today_str = datetime.now().strftime("%Y-%m-%d")
        self.assertIn(f'last_indexed: "{today_str}"', pruned_content)

    def test_prune_gemini_workstreams(self):
        """Verifies Done workstreams are archived to docs/workstreams/archive.md."""
        pruned_content, result = prune_gemini_md(SAMPLE_GEMINI_MD, self.repo_root, keep_learnings=7)

        # 1. Done rows (#1 and #3) must NOT be in Section 5 table
        self.assertNotIn("`#1` | Audio DSP | Done", pruned_content)
        self.assertNotIn("`#3` | Docs Sync | Done", pruned_content)

        # 2. In Progress row (#2) must be preserved
        self.assertIn("`#2` | Video Pipeline | In Progress", pruned_content)

        # 3. docs/workstreams/archive.md must exist and contain the archived rows
        archive_path = self.repo_root / "docs" / "workstreams" / "archive.md"
        self.assertTrue(archive_path.exists())
        archive_text = archive_path.read_text(encoding="utf-8")
        self.assertIn("Audio DSP", archive_text)
        self.assertIn("Docs Sync", archive_text)

        # 4. Pointer note must be present in Section 5
        self.assertIn("> [!NOTE]", pruned_content)
        self.assertIn("completed workstreams archived to [docs/workstreams/archive.md](docs/workstreams/archive.md)", pruned_content)

    def test_prune_gemini_all_workstreams_done(self):
        """Verifies placeholder row when all workstreams are Done."""
        content_all_done = SAMPLE_GEMINI_MD.replace(
            "| `#2` | Video Pipeline | In Progress | `#1` | `pytest` |",
            "| `#2` | Video Pipeline | Done | `#1` | `pytest` |"
        )
        pruned_content, result = prune_gemini_md(content_all_done, self.repo_root, keep_learnings=7)

        # Placeholder row must replace active workstreams
        self.assertIn("| - | *No active workstreams* | - | - | - |", pruned_content)
        self.assertIn("3 completed workstreams archived to [docs/workstreams/archive.md](docs/workstreams/archive.md)", pruned_content)

    def test_prune_gemini_learnings(self):
        """Verifies excess learnings are archived to docs/error-solving/understood-errors.md."""
        pruned_content, result = prune_gemini_md(SAMPLE_GEMINI_MD, self.repo_root, keep_learnings=5)

        # 1. Only top 5 learnings must remain in GEMINI.md
        self.assertIn("[LEARNING-001]", pruned_content)
        self.assertIn("[LEARNING-005]", pruned_content)
        self.assertNotIn("[LEARNING-006]", pruned_content)
        self.assertNotIn("[LEARNING-009]", pruned_content)

        # 2. Complete catalog must be in docs/error-solving/understood-errors.md
        errors_path = self.repo_root / "docs" / "error-solving" / "understood-errors.md"
        self.assertTrue(errors_path.exists())
        errors_text = errors_path.read_text(encoding="utf-8")
        self.assertIn("[LEARNING-001]", errors_text)
        self.assertIn("[LEARNING-009]", errors_text)

        # 3. Pointer note must be present
        self.assertIn("> [!NOTE]", pruned_content)
        self.assertIn(
            "Complete catalog of failure modes and mitigation patterns indexed in [docs/error-solving/understood-errors.md](docs/error-solving/understood-errors.md)",
            pruned_content,
        )

    def test_prune_continuity_history(self):
        """Verifies - Historical Archive: moved to docs/sessions/history/archive.md."""
        pruned_content, result = prune_continuity_md(SAMPLE_CONTINUITY_MD, self.repo_root)

        # 1. Individual milestone bullets must not be in CONTINUITY.md
        self.assertNotIn("Milestone 1: Initial prototype designed", pruned_content)
        self.assertNotIn("Milestone 5: CI workflow verified", pruned_content)

        # 2. Canonical schema must be preserved
        self.assertIn("- Goal (incl. success criteria):", pruned_content)
        self.assertIn("- Constraints/Assumptions:", pruned_content)
        self.assertIn("- Key decisions:", pruned_content)
        self.assertIn("- State:", pruned_content)
        self.assertIn("Done:", pruned_content)
        self.assertIn("Now:", pruned_content)
        self.assertIn("Next:", pruned_content)
        self.assertIn("- Open questions:", pruned_content)
        self.assertIn("- Working set (files/ids/commands):", pruned_content)

        # 3. Historical Archive pointer must be present
        self.assertIn("- Historical Archive:", pruned_content)
        self.assertIn("Past session milestones archived to [docs/sessions/history/archive.md](docs/sessions/history/archive.md)", pruned_content)

        # 4. Target archive file must exist and contain milestone bullets
        archive_path = self.repo_root / "docs" / "sessions" / "history" / "archive.md"
        self.assertTrue(archive_path.exists())
        archive_text = archive_path.read_text(encoding="utf-8")
        self.assertIn("Milestone 1: Initial prototype designed", archive_text)
        self.assertIn("Milestone 5: CI workflow verified", archive_text)

    def test_dry_run_does_not_mutate(self):
        """Verifies --dry-run leaves files untouched."""
        gemini_file = self.repo_root / "GEMINI.md"
        gemini_file.write_text(SAMPLE_GEMINI_MD, encoding="utf-8")
        orig_content = gemini_file.read_text(encoding="utf-8")

        # Run with dry_run=True
        pruned_content, result = prune_gemini_md(orig_content, self.repo_root, keep_learnings=7, dry_run=True)

        # Assert GEMINI.md was NOT modified
        self.assertEqual(gemini_file.read_text(encoding="utf-8"), orig_content)

        # Assert no docs/specs or docs/workstreams files were written to disk
        self.assertFalse((self.repo_root / "docs" / "specs").exists())
        self.assertFalse((self.repo_root / "docs" / "workstreams" / "archive.md").exists())

    def test_metrics_calculation(self):
        """Verifies line, byte, and token calculation and table formatting."""
        stats_before = {"lines": 100, "bytes": 4000, "tokens": 1000}
        stats_after = {"lines": 50, "bytes": 2000, "tokens": 500}

        table = format_metrics_table(stats_before, stats_after, "GEMINI.md")
        self.assertIn("GEMINI.md", table)
        self.assertIn("Lines", table)
        self.assertIn("Bytes", table)
        self.assertIn("Tokens", table)
        self.assertIn("50.0%", table)

    def test_atomic_backup_rotation(self):
        """Verifies max 3 rotating .bak files are maintained."""
        target_file = self.repo_root / "test_doc.md"
        target_file.write_text("v1", encoding="utf-8")
        rotate_backups(target_file, max_backups=3)

        target_file.write_text("v2", encoding="utf-8")
        rotate_backups(target_file, max_backups=3)

        target_file.write_text("v3", encoding="utf-8")
        rotate_backups(target_file, max_backups=3)

        target_file.write_text("v4", encoding="utf-8")
        rotate_backups(target_file, max_backups=3)

        bak_files = list(self.repo_root.glob("test_doc.md.*.bak"))
        self.assertEqual(len(bak_files), 3)

    def test_cli_apply_and_json(self):
        """Verifies CLI execution with --apply and --json."""
        target_file = self.repo_root / "GEMINI.md"
        target_file.write_text(SAMPLE_GEMINI_MD, encoding="utf-8")

        cli_script = SCRIPT_DIR / "prune_context.py"
        cmd = [
            sys.executable,
            str(cli_script),
            "--file",
            str(target_file),
            "--apply",
            "--json",
            "--root",
            str(self.repo_root),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, f"CLI stderr: {result.stderr}")

        data = json.loads(result.stdout)
        self.assertIn("files", data)
        self.assertEqual(len(data["files"]), 1)
        file_info = data["files"][0]
        self.assertIn("stats_before", file_info)
        self.assertIn("stats_after", file_info)
        self.assertGreater(file_info["stats_before"]["lines"], 0)
        self.assertGreater(file_info["stats_after"]["lines"], 0)
        self.assertTrue((self.repo_root / "docs" / "specs" / "adaptive-production.md").exists())

    def test_cli_all_flag(self):
        """Verifies CLI execution with --all flag."""
        gemini_file = self.repo_root / "GEMINI.md"
        gemini_file.write_text(SAMPLE_GEMINI_MD, encoding="utf-8")
        continuity_file = self.repo_root / "CONTINUITY.md"
        continuity_file.write_text(SAMPLE_CONTINUITY_MD, encoding="utf-8")

        cli_script = SCRIPT_DIR / "prune_context.py"
        cmd = [
            sys.executable,
            str(cli_script),
            "--all",
            "--dry-run",
            "--json",
            "--root",
            str(self.repo_root),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, f"CLI stderr: {result.stderr}")

        data = json.loads(result.stdout)
        self.assertEqual(len(data["files"]), 2)
        filenames = {f["file"] for f in data["files"]}
        self.assertEqual(filenames, {"GEMINI.md", "CONTINUITY.md"})

    def test_5_tier_anatomy_strict_compliance(self):
        """Verifies pruned output conforms to 5-Tier Anatomy validator without errors."""
        from validate_gemini_md import validate_markdown

        gemini_file = self.repo_root / "GEMINI.md"
        pruned_content, result = prune_gemini_md(
            SAMPLE_GEMINI_MD, self.repo_root, keep_learnings=7, dry_run=False
        )
        gemini_file.write_text(pruned_content, encoding="utf-8")

        diagnostics = validate_markdown(pruned_content, gemini_file, self.repo_root)
        self.assertEqual(
            diagnostics["errors"],
            [],
            f"Validation errors found on pruned content: {diagnostics['errors']}",
        )


if __name__ == "__main__":
    unittest.main()

