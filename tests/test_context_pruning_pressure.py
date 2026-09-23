"""tests/test_context_pruning_pressure.py

End-to-end pressure scenario testing for scripts/prune_context.py directly against
the user's downloaded real-world files:
- C:\\Users\\Snoozer\\Downloads\\GEMINI.md
- C:\\Users\\Snoozer\\Downloads\\CONTINUITY.md

Python standard library only.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = REPO_ROOT / ".agents" / "skills" / "gemini-context-engineer"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from prune_context import prune_gemini_md, prune_continuity_md
from validate_gemini_md import get_federation_banner, classify_federation_file

SAMPLE_GEMINI_PATH = Path(r"C:\Users\Snoozer\Downloads\GEMINI.md")
SAMPLE_CONTINUITY_PATH = Path(r"C:\Users\Snoozer\Downloads\CONTINUITY.md")


class TestContextPruningPressure(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        if sys.platform == "win32":
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _populate_workspace_stubs(self, root: Path, content: str):
        """Creates on-disk stub files for all referenced relative links in GEMINI.md."""
        links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
        for _text, url in links:
            if url.startswith("http://") or url.startswith("https://") or url.startswith("#"):
                continue
            path_str = url.split("#")[0].replace("\\", "/")
            if not path_str:
                continue
            target = root / path_str
            if path_str.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    if target.name == "AGENTS.md":
                        banner = get_federation_banner("AGENTS.md")
                        target.write_text(f"{banner}\n\n# Custom Agents\n", encoding="utf-8")
                    elif target.name == "CLAUDE.md":
                        banner = get_federation_banner("CLAUDE.md")
                        target.write_text(f"{banner}\n\n# Custom Claude\n", encoding="utf-8")
                    else:
                        target.write_text("# stub\n", encoding="utf-8")

    def test_pressure_prune_downloaded_gemini_md(self):
        """Tests pruning directly on C:\\Users\\Snoozer\\Downloads\\GEMINI.md.

        Verifies:
        - Sharding of rogue section '## Adaptive multi-channel production'
        - Invariants preserved in Section 3 under '### Technical & Environmental Invariants'
        - Exactly 5 H2 headers
        - 29 Done workstreams archived to docs/workstreams/archive.md
        - 41 learnings archived to docs/error-solving/understood-errors.md
        - Line count reduction >= 30%
        - Token reduction >= 60% (<= 3,500 tokens)
        - Passes validate_gemini_md.py --strict --reality with exit code 0
        """
        self.assertTrue(SAMPLE_GEMINI_PATH.exists(), f"Sample file not found: {SAMPLE_GEMINI_PATH}")
        raw_content = SAMPLE_GEMINI_PATH.read_text(encoding="utf-8")

        # Execute pruning with keep_learnings=7
        pruned_content, result = prune_gemini_md(
            raw_content, self.workspace, keep_learnings=7, dry_run=False
        )

        gemini_dest = self.workspace / "GEMINI.md"
        gemini_dest.write_text(pruned_content, encoding="utf-8")

        # 1. Assert rogue section sharded
        sharded_spec = self.workspace / "docs" / "specs" / "adaptive-production.md"
        self.assertTrue(sharded_spec.exists(), "docs/specs/adaptive-production.md must exist")
        sharded_text = sharded_spec.read_text(encoding="utf-8")
        self.assertIn("Adaptive multi-channel production", sharded_text)
        self.assertNotIn("## Adaptive multi-channel production", pruned_content)

        # 2. Invariants preserved in Section 3
        self.assertIn("### Technical & Environmental Invariants", pruned_content)
        self.assertIn("filter_complex", pruned_content)
        self.assertIn("No DNS", pruned_content)
        self.assertIn("Intel QSV Compositing", pruned_content)
        self.assertGreaterEqual(result["extracted_invariants_count"], 1)

        # 3. Exactly 5 H2 headers present
        h2_headers = [line.strip() for line in pruned_content.splitlines() if line.startswith("## ")]
        self.assertEqual(len(h2_headers), 5, f"Expected 5 H2 headers, got: {h2_headers}")

        # 4. 29 Done workstreams archived
        workstreams_archive = self.workspace / "docs" / "workstreams" / "archive.md"
        self.assertTrue(workstreams_archive.exists(), "docs/workstreams/archive.md must exist")
        self.assertEqual(result["archived_workstreams_count"], 29)
        archive_text = workstreams_archive.read_text(encoding="utf-8")
        self.assertIn("#1", archive_text)
        self.assertIn("#30", archive_text)

        # 5. 41 learnings archived to understood-errors.md
        errors_path = self.workspace / "docs" / "error-solving" / "understood-errors.md"
        self.assertTrue(errors_path.exists(), "docs/error-solving/understood-errors.md must exist")
        errors_text = errors_path.read_text(encoding="utf-8")
        self.assertIn("[LEARNING-001]", errors_text)
        self.assertIn("[LEARNING-048]", errors_text)
        # Pruned content must retain top 7 learnings
        self.assertIn("[LEARNING-001]", pruned_content)
        self.assertIn("[LEARNING-007]", pruned_content)
        self.assertNotIn("[LEARNING-008]", pruned_content)

        # 6. Reductions: lines >= 30%, tokens >= 60% (<= 3500 tokens)
        self.assertGreaterEqual(
            result["delta_lines_pct"], 30.0, f"Line reduction {result['delta_lines_pct']}% < 30%"
        )
        self.assertGreaterEqual(
            result["delta_tokens_pct"], 60.0, f"Token reduction {result['delta_tokens_pct']}% < 60%"
        )
        self.assertLessEqual(
            result["stats_after"]["tokens"], 3500, f"Tokens {result['stats_after']['tokens']} > 3500"
        )

        # 7. Validation: validate_gemini_md.py --strict --reality with exit code 0
        self._populate_workspace_stubs(self.workspace, pruned_content)
        val_script = SCRIPTS_DIR / "validate_gemini_md.py"
        cmd = [
            sys.executable,
            str(val_script),
            str(gemini_dest),
            "--strict",
            "--reality",
        ]
        proc = subprocess.run(
            cmd,
            cwd=str(self.workspace),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"Validator failed with code {proc.returncode}.\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}",
        )

    def test_pressure_prune_downloaded_continuity_md(self):
        """Tests pruning directly on C:\\Users\\Snoozer\\Downloads\\CONTINUITY.md.

        Verifies:
        - Milestones moved to docs/sessions/history/archive.md
        - Canonical schema intact (Goal, Constraints, Key decisions, State, Open questions)
        - Line count reduction >= 75% (down from 334 lines to <= 70 lines)
        - Token reduction >= 80% (down from ~12,500 tokens to <= 2,200 tokens)
        - Repeated pruning on output is 100% idempotent (0 additional lines added)
        """
        self.assertTrue(
            SAMPLE_CONTINUITY_PATH.exists(), f"Sample file not found: {SAMPLE_CONTINUITY_PATH}"
        )
        raw_content = SAMPLE_CONTINUITY_PATH.read_text(encoding="utf-8")

        # First pass pruning
        pruned_content, result = prune_continuity_md(raw_content, self.workspace, dry_run=False)

        continuity_dest = self.workspace / "CONTINUITY.md"
        continuity_dest.write_text(pruned_content, encoding="utf-8")

        # 1. Milestones moved to docs/sessions/history/archive.md
        archive_path = self.workspace / "docs" / "sessions" / "history" / "archive.md"
        self.assertTrue(archive_path.exists(), "docs/sessions/history/archive.md must exist")
        archive_text = archive_path.read_text(encoding="utf-8")
        self.assertIn("Phase 1 & 2: Script Translation", archive_text)
        self.assertIn("Phase 10 YouTube Thumbnail Packaging", archive_text)
        self.assertGreaterEqual(result["archived_milestones_count"], 50)

        # 2. Canonical schema intact
        self.assertIn("- Goal (incl. success criteria):", pruned_content)
        self.assertIn("- Constraints/Assumptions:", pruned_content)
        self.assertIn("- Key decisions:", pruned_content)
        self.assertIn("- State:", pruned_content)
        self.assertIn("Done:", pruned_content)
        self.assertIn("Now:", pruned_content)
        self.assertIn("Next:", pruned_content)
        self.assertIn("- Open questions:", pruned_content)
        self.assertIn("- Working set (files/ids/commands):", pruned_content)

        # 3. Line count reduction >= 75%, lines <= 70
        self.assertGreaterEqual(
            result["delta_lines_pct"], 75.0, f"Line reduction {result['delta_lines_pct']}% < 75%"
        )
        self.assertLessEqual(
            result["stats_after"]["lines"], 70, f"Line count {result['stats_after']['lines']} > 70"
        )

        # 4. Token reduction >= 80%, tokens <= 2200
        self.assertGreaterEqual(
            result["delta_tokens_pct"], 80.0, f"Token reduction {result['delta_tokens_pct']}% < 80%"
        )
        self.assertLessEqual(
            result["stats_after"]["tokens"],
            2200,
            f"Token count {result['stats_after']['tokens']} > 2200",
        )

        # 5. Idempotency assertion: re-running on output adds 0 additional lines
        archive_lines_count_1 = len(archive_path.read_text(encoding="utf-8").splitlines())
        pruned_content_2, result_2 = prune_continuity_md(
            pruned_content, self.workspace, dry_run=False
        )
        archive_lines_count_2 = len(archive_path.read_text(encoding="utf-8").splitlines())

        self.assertEqual(
            result_2["archived_milestones_count"],
            0,
            f"Expected 0 milestones archived on second pass, got {result_2['archived_milestones_count']}",
        )
        self.assertEqual(
            archive_lines_count_1,
            archive_lines_count_2,
            f"Archive file grew by {archive_lines_count_2 - archive_lines_count_1} lines on second pass",
        )
        self.assertEqual(pruned_content, pruned_content_2)

    def test_pressure_cross_agent_federation_with_pruning(self):
        """Tests that federation maintains custom instructions and validates without split-brain warnings.

        Verifies:
        - Creates repo with GEMINI.md, AGENTS.md, and CLAUDE.md
        - Runs validate_gemini_md.py --federate
        - Both AGENTS.md and CLAUDE.md retain full custom instructions
        - Authoritative directive banner present at line 1
        - Zero split-brain warnings
        """
        gemini_content = """---
project_name: "federation-pressure-test"
version: "1.0.0"
tech_stack:
  - "python"
rules:
  - "stdlib-only"
exclude_paths:
  - ".git"
last_indexed: "2026-09-24"
generator: "gemini-context-engineer/v4.0.0"
---

# Project Context: federation-pressure-test

## 🎯 Project Overview
Federation pressure test overview.

## 🏗️ Architecture & Component Mapping
```text
System A -> System B
```

| Domain | Package | Entrypoint | Key Responsibility |
| :--- | :--- | :--- | :--- |
| Core | core/ | main.py | Core functionality |

### Domain Lexicon & Ubiquitous Language
| Term | Canonical Meaning | Forbidden Synonyms |
| :--- | :--- | :--- |
| `Task` | Unit of work | "Job" |

## 🛑 Mandatory Engineering Constraints
- Standard library only.

## 🛠️ Common Workflows & CLI Commands
- Run tests: `python -m unittest`

## 🔄 Active Workstreams & Verification Status
| ID | Workstream Slice | Status | Blocked By | Proof Command |
| :--- | :--- | :--- | :--- | :--- |
| `#1` | Base Slice | Done | - | `python -m unittest` |
"""
        (self.workspace / "GEMINI.md").write_text(gemini_content, encoding="utf-8")

        custom_opencode_instructions = (
            "# Custom OpenCode Orchestrator Config\n"
            "Subagent permissions: read: allow, edit: deny, bash: deny.\n"
            "Default agent: orchestrator.\n"
        )
        custom_claude_instructions = (
            "# Custom Claude CLI Instructions\n"
            "Always prefer concise diff outputs and execute tests after edits.\n"
        )

        (self.workspace / "AGENTS.md").write_text(custom_opencode_instructions, encoding="utf-8")
        (self.workspace / "CLAUDE.md").write_text(custom_claude_instructions, encoding="utf-8")

        # Create core/ and main.py stub
        core_dir = self.workspace / "core"
        core_dir.mkdir(parents=True, exist_ok=True)
        (core_dir / "main.py").write_text("# core\n", encoding="utf-8")

        # Run validate_gemini_md.py --federate
        val_script = SCRIPTS_DIR / "validate_gemini_md.py"
        cmd = [
            sys.executable,
            str(val_script),
            str(self.workspace / "GEMINI.md"),
            "--federate",
            "--strict",
            "--reality",
        ]
        proc = subprocess.run(
            cmd,
            cwd=str(self.workspace),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"Federation validation failed with code {proc.returncode}.\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}",
        )

        agents_after = (self.workspace / "AGENTS.md").read_text(encoding="utf-8")
        claude_after = (self.workspace / "CLAUDE.md").read_text(encoding="utf-8")

        # 1. Custom instructions preserved
        self.assertIn("Subagent permissions: read: allow, edit: deny, bash: deny.", agents_after)
        self.assertIn("Always prefer concise diff outputs and execute tests after edits.", claude_after)

        # 2. Authoritative directive at line 1
        self.assertTrue(
            agents_after.startswith("<!-- AGENT-SYNC: GEMINI.md:start -->"),
            f"AGENTS.md must start with directive banner, got: {agents_after[:80]}",
        )
        self.assertTrue(
            claude_after.startswith("<!-- AGENT-SYNC: GEMINI.md:start -->"),
            f"CLAUDE.md must start with directive banner, got: {claude_after[:80]}",
        )

        # 3. Classification is federated_hybrid
        status_agents, _ = classify_federation_file(self.workspace / "AGENTS.md")
        status_claude, _ = classify_federation_file(self.workspace / "CLAUDE.md")
        self.assertEqual(status_agents, "federated_hybrid")
        self.assertEqual(status_claude, "federated_hybrid")

    def test_h2_parsing_ignores_code_fences(self):
        """Verifies that lines starting with '## ' inside code fences (``` or ~~~) are ignored."""
        content_with_fenced_h2 = """---
project_name: "fence-test"
version: "1.0.0"
tech_stack:
  - "python"
rules:
  - "stdlib-only"
exclude_paths:
  - ".git"
last_indexed: "2026-09-24"
generator: "gemini-context-engineer/v4.0.0"
---

# Project Context: fence-test

## 🎯 Project Overview
Test project overview.

```markdown
## Fake Rogue Header Inside Backticks
This is inside a markdown code block.
```

~~~bash
## Fake Rogue Header Inside Tildes
echo "hello"
~~~

## 🏗️ Architecture & Component Mapping
```text
A -> B
```

| Domain | Package | Entrypoint | Key Responsibility |
| :--- | :--- | :--- | :--- |
| Audio | audio/ | main.py | Audio |

### Domain Lexicon & Ubiquitous Language
| Term | Canonical Meaning | Forbidden Synonyms |
| :--- | :--- | :--- |
| `Item` | Item | "Thing" |

## 🛑 Mandatory Engineering Constraints
- Standard library only.

## 🛠️ Common Workflows & CLI Commands
- Run tests: `pytest`

## 🔄 Active Workstreams & Verification Status
| ID | Workstream Slice | Status | Blocked By | Proof Command |
| :--- | :--- | :--- | :--- | :--- |
| `#1` | Slice 1 | Done | - | `pytest` |
"""
        pruned_content, result = prune_gemini_md(
            content_with_fenced_h2, self.workspace, keep_learnings=7, dry_run=False
        )

        # The fenced headers must NOT be sharded or treated as rogue H2 sections
        self.assertFalse(
            (self.workspace / "docs" / "specs" / "fake-rogue-header-inside-backticks.md").exists()
        )
        self.assertFalse(
            (self.workspace / "docs" / "specs" / "fake-rogue-header-inside-tildes.md").exists()
        )
        # Content inside the code block should remain intact
        self.assertIn("## Fake Rogue Header Inside Backticks", pruned_content)
        self.assertIn("## Fake Rogue Header Inside Tildes", pruned_content)

    def test_line_ending_normalization_crlf(self):
        """Verifies that CRLF input is normalized to LF (\\n) in frontmatter and output."""
        crlf_content = (
            "---\r\n"
            "project_name: \"crlf-test\"\r\n"
            "version: \"1.0.0\"\r\n"
            "tech_stack:\r\n"
            "  - \"python\"\r\n"
            "rules:\r\n"
            "  - \"stdlib-only\"\r\n"
            "exclude_paths:\r\n"
            "  - \".git\"\r\n"
            "last_indexed: \"2020-01-01\"\r\n"
            "generator: \"gemini-context-engineer/v4.0.0\"\r\n"
            "---\r\n"
            "\r\n"
            "# Project Context: crlf-test\r\n"
            "\r\n"
            "## 🎯 Project Overview\r\n"
            "Overview with CRLF.\r\n"
            "\r\n"
            "## 🏗️ Architecture & Component Mapping\r\n"
            "| Domain | Package | Entrypoint | Key Responsibility |\r\n"
            "| :--- | :--- | :--- | :--- |\r\n"
            "| Core | core/ | main.py | Core |\r\n"
            "\r\n"
            "### Domain Lexicon & Ubiquitous Language\r\n"
            "| Term | Canonical Meaning | Forbidden Synonyms |\r\n"
            "| :--- | :--- | :--- |\r\n"
            "| `Term` | Meaning | \"Bad\" |\r\n"
            "\r\n"
            "## 🛑 Mandatory Engineering Constraints\r\n"
            "- Constraint.\r\n"
            "\r\n"
            "## 🛠️ Common Workflows & CLI Commands\r\n"
            "- Command.\r\n"
            "\r\n"
            "## 🔄 Active Workstreams & Verification Status\r\n"
            "| ID | Workstream Slice | Status | Blocked By | Proof Command |\r\n"
            "| :--- | :--- | :--- | :--- | :--- |\r\n"
            "| `#1` | Slice | Done | - | `test` |\r\n"
        )
        pruned_content, result = prune_gemini_md(
            crlf_content, self.workspace, keep_learnings=7, dry_run=False
        )

        self.assertNotIn("\r\n", pruned_content, "Output must be normalized to LF (\\n)")
        self.assertTrue(pruned_content.startswith("---\n"))


if __name__ == "__main__":
    unittest.main()
