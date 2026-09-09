import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Add parent directory to sys.path to import validator
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.validate_gemini_md import parse_micro_yaml, rotate_backups, validate_markdown


class TestValidator(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.test_dir.name).resolve()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_micro_yaml_parser(self):
        yaml_content = """---
key1: value1
flow_list: ["a", "b"]
multi_line:
  - item1
  - item2
# inline comment
key2: val2 # comment
---
"""
        crlf_content = yaml_content.replace("\n", "\r\n")
        bom_content = "\ufeff" + yaml_content

        for content in [yaml_content, crlf_content, bom_content]:
            parsed = parse_micro_yaml(content)
            self.assertEqual(parsed.get("key1"), "value1")
            self.assertEqual(parsed.get("flow_list"), ["a", "b"])
            self.assertEqual(parsed.get("multi_line"), ["item1", "item2"])
            self.assertEqual(parsed.get("key2"), "val2")

    def get_valid_frontmatter(self):
        return """---
project_name: "test"
version: "1.0.0"
tech_stack: []
rules: []
exclude_paths: []
last_indexed: "2026-09-03"
---
"""

    def test_headers(self):
        content = self.get_valid_frontmatter() + "# Project Context: Main Title\n"
        required_h2s = [
            "## 🎯 Project Overview",
            "## 🏗️ Architecture & Component Mapping",
            "## 🛑 Mandatory Engineering Constraints",
            "## 🛠️ Common Workflows & CLI Commands",
            "## 🔄 Active Workstreams & Verification Status",
        ]
        content += "\n".join(required_h2s) + "\n"

        diag = validate_markdown(content, self.test_path / "test.md", self.test_path)
        self.assertEqual(len(diag["errors"]), 0)

        content_with_unicode = (
            self.get_valid_frontmatter()
            + "# Project Context: Main Title\ufe0f\n"
            + "\n".join([h + "\ufe0f" for h in required_h2s])
            + "\n"
        )
        diag2 = validate_markdown(content_with_unicode, self.test_path / "test.md", self.test_path)
        self.assertEqual(len(diag2["errors"]), 0)

        bad_content = self.get_valid_frontmatter() + "## Section 1\n"
        diag3 = validate_markdown(bad_content, self.test_path / "test.md", self.test_path)
        self.assertGreater(len(diag3["errors"]), 0)

    def test_dual_budget_validation(self):
        pass_content = self.get_valid_frontmatter() + "a\n" * 300
        diag = validate_markdown(pass_content, self.test_path / "test.md", self.test_path)
        self.assertEqual(
            len([w for w in diag["warnings"] if "WARN_BUDGET_APPROACHING: Line count" in w]), 0
        )
        self.assertEqual(
            len([e for e in diag["errors"] if "ERR_BUDGET_EXCEEDED: Line count" in e]), 0
        )

        warn_content = self.get_valid_frontmatter() + "a\n" * 400
        diag2 = validate_markdown(warn_content, self.test_path / "test.md", self.test_path)
        self.assertEqual(
            len([w for w in diag2["warnings"] if "WARN_BUDGET_APPROACHING: Line count" in w]), 1
        )

        err_content = self.get_valid_frontmatter() + "a\n" * 600
        diag3 = validate_markdown(err_content, self.test_path / "test.md", self.test_path)
        self.assertEqual(
            len([e for e in diag3["errors"] if "ERR_BUDGET_EXCEEDED: Line count" in e]), 1
        )

        long_line = self.get_valid_frontmatter() + "a" * (4 * 3600) + "\n"
        diag4 = validate_markdown(long_line, self.test_path / "test.md", self.test_path)
        self.assertEqual(
            len([e for e in diag4["errors"] if "ERR_BUDGET_EXCEEDED: Token count" in e]), 1
        )

    def test_link_resolution(self):
        (self.test_path / "test.txt").touch()

        content1 = self.get_valid_frontmatter() + "[link](file://test.txt)"
        diag1 = validate_markdown(content1, self.test_path / "test.md", self.test_path)
        self.assertEqual(len([e for e in diag1["errors"] if "ERR_BROKEN_LINK" in e]), 0)

        content2 = self.get_valid_frontmatter() + "[broken](file://missing.txt)"
        diag2 = validate_markdown(content2, self.test_path / "test.md", self.test_path)
        self.assertGreater(len(diag2["errors"]), 0)
        self.assertTrue(any("missing.txt" in e for e in diag2["errors"]))

        content3 = self.get_valid_frontmatter() + "[anchor](file://test.txt#L10)"
        diag3 = validate_markdown(content3, self.test_path / "test.md", self.test_path)
        self.assertEqual(len([e for e in diag3["errors"] if "ERR_BROKEN_LINK" in e]), 0)

        content4 = self.get_valid_frontmatter() + "[inpage](#heading)"
        diag4 = validate_markdown(content4, self.test_path / "test.md", self.test_path)
        self.assertEqual(len([e for e in diag4["errors"] if "ERR_BROKEN_LINK" in e]), 0)

    def test_rotating_backups(self):
        base_file = self.test_path / "GEMINI.md"
        base_file.touch()
        for i in range(5):
            (self.test_path / f"GEMINI.md.20260903_12000{i}_123456.bak").touch()

        rotate_backups(base_file)
        baks = list(self.test_path.glob("*.bak"))
        self.assertEqual(len(baks), 3)

    def test_strict_mode(self):
        content = self.get_valid_frontmatter() + "# Project Context: Main Title\n"
        required_h2s = [
            "## 🎯 Project Overview",
            "## 🏗️ Architecture & Component Mapping",
            "## 🛑 Mandatory Engineering Constraints",
            "## 🛠️ Common Workflows & CLI Commands",
            "## 🔄 Active Workstreams & Verification Status",
        ]
        content += "\n".join(required_h2s) + "\n"
        # Add an external link to trigger a warning
        content += "[ext](https://example.com)"

        (self.test_path / "test.md").write_text(content, encoding="utf-8")

        res1 = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent.parent / "scripts" / "validate_gemini_md.py"),
                str(self.test_path / "test.md"),
            ]
        )
        self.assertEqual(res1.returncode, 0)

        res2 = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent.parent / "scripts" / "validate_gemini_md.py"),
                str(self.test_path / "test.md"),
                "--strict",
            ]
        )
        self.assertEqual(res2.returncode, 1)

    def test_split_brain_context_warning(self):
        (self.test_path / "GEMINI.md").touch()
        (self.test_path / "CLAUDE.md").write_text("Some divergent context", encoding="utf-8")

        content = self.get_valid_frontmatter() + "# Project Context: Main Title\n"
        required_h2s = [
            "## 🎯 Project Overview",
            "## 🏗️ Architecture & Component Mapping",
            "## 🛑 Mandatory Engineering Constraints",
            "## 🛠️ Common Workflows & CLI Commands",
            "## 🔄 Active Workstreams & Verification Status",
        ]
        content += "\n".join(required_h2s) + "\n"

        diag = validate_markdown(content, self.test_path / "GEMINI.md", self.test_path)
        self.assertTrue(any("WARN_SPLIT_BRAIN_CONTEXT" in w for w in diag["warnings"]))

    def test_child_index_validation(self):
        sub_dir = self.test_path / "sub"
        sub_dir.mkdir()
        (sub_dir / "GEMINI.md").touch()

        content = self.get_valid_frontmatter() + "# Project Context: Main Title\n"
        required_h2s = [
            "## 🎯 Project Overview",
            "## 🏗️ Architecture & Component Mapping",
            "## 🛑 Mandatory Engineering Constraints",
            "## 🛠️ Common Workflows & CLI Commands",
            "## 🔄 Active Workstreams & Verification Status",
        ]
        content += "\n".join(required_h2s) + "\n"

        diag1 = validate_markdown(content, self.test_path / "GEMINI.md", self.test_path)
        self.assertTrue(any("WARN_CHILD_INDEX_INCOMPLETE" in w for w in diag1["warnings"]))

        required_h2s_with_ref = [
            "## 🎯 Project Overview",
            "## 🏗️ Architecture & Component Mapping\nsub/GEMINI.md",
            "## 🛑 Mandatory Engineering Constraints",
            "## 🛠️ Common Workflows & CLI Commands",
            "## 🔄 Active Workstreams & Verification Status",
        ]
        content_with_ref = (
            self.get_valid_frontmatter()
            + "# Project Context: Main Title\n"
            + "\n".join(required_h2s_with_ref)
            + "\n"
        )

        diag2 = validate_markdown(content_with_ref, self.test_path / "GEMINI.md", self.test_path)
        self.assertFalse(any("WARN_CHILD_INDEX_INCOMPLETE" in w for w in diag2["warnings"]))

    def test_failure_modes_ledger(self):
        content = self.get_valid_frontmatter() + "# Project Context: Main Title\n"
        required_h2s = [
            "## 🎯 Project Overview",
            "## 🏗️ Architecture & Component Mapping",
            "## 🛑 Mandatory Engineering Constraints",
            "## 🛠️ Common Workflows & CLI Commands",
            "## 🔄 Active Workstreams & Verification Status\n### Known Failure Modes & Project Learnings\n",
        ]
        content += "\n".join(required_h2s) + "\n"

        diag = validate_markdown(content, self.test_path / "GEMINI.md", self.test_path)
        self.assertEqual(len(diag["errors"]), 0)

    def test_dag_cycle_detection(self):
        content = self.get_valid_frontmatter() + "# Project Context: Main Title\n"
        required_h2s = [
            "## 🎯 Project Overview",
            "## 🏗️ Architecture & Component Mapping",
            "## 🛑 Mandatory Engineering Constraints",
            "## 🛠️ Common Workflows & CLI Commands",
            "## 🔄 Active Workstreams & Verification Status",
        ]
        content += "\n".join(required_h2s) + "\n"

        cycle_content = content + (
            "| #1 | Slice 1 | In Progress | Blocked by: #2 |\n"
            "| #2 | Slice 2 | In Progress | Blocked by: #1 |\n"
        )
        diag = validate_markdown(cycle_content, self.test_path / "GEMINI.md", self.test_path)
        self.assertTrue(any("ERR_DAG_CYCLE" in e for e in diag["errors"]))

        acyclic_content = content + (
            "| #1 | Slice 1 | In Progress | |\n" "| #2 | Slice 2 | In Progress | Blocked by: #1 |\n"
        )
        diag_acyclic = validate_markdown(
            acyclic_content, self.test_path / "GEMINI.md", self.test_path
        )
        self.assertFalse(any("ERR_DAG_CYCLE" in e for e in diag_acyclic["errors"]))

    def test_reality_drift_detection(self):
        content = self.get_valid_frontmatter() + "# Project Context: Main Title\n"
        required_h2s = [
            "## 🎯 Project Overview",
            "## 🏗️ Architecture & Component Mapping\n[missing](missing_file.py)",
            "## 🛑 Mandatory Engineering Constraints",
            "## 🛠️ Common Workflows & CLI Commands",
            "## 🔄 Active Workstreams & Verification Status",
        ]
        content += "\n".join(required_h2s) + "\n"

        diag = validate_markdown(
            content, self.test_path / "GEMINI.md", self.test_path, reality=True
        )
        self.assertTrue(any("WARN_REALITY_DRIFT" in w for w in diag["warnings"]))

    def test_domain_lexicon_parsing(self):
        content = self.get_valid_frontmatter() + "# Project Context: Main Title\n"
        required_h2s = [
            "## 🎯 Project Overview\n### Domain Lexicon & Ubiquitous Language\n| Term | Definition |\n|---|---|\n| Foo | Bar |",
            "## 🏗️ Architecture & Component Mapping",
            "## 🛑 Mandatory Engineering Constraints",
            "## 🛠️ Common Workflows & CLI Commands",
            "## 🔄 Active Workstreams & Verification Status",
        ]
        content += "\n".join(required_h2s) + "\n"

        diag = validate_markdown(content, self.test_path / "GEMINI.md", self.test_path)
        self.assertEqual(len(diag["errors"]), 0)

    def test_context_file_flag_aliases(self):
        content = self.get_valid_frontmatter() + "# Project Context: Main Title\n"
        required_h2s = [
            "## 🎯 Project Overview",
            "## 🏗️ Architecture & Component Mapping",
            "## 🛑 Mandatory Engineering Constraints",
            "## 🛠️ Common Workflows & CLI Commands",
            "## 🔄 Active Workstreams & Verification Status",
        ]
        content += "\n".join(required_h2s) + "\n"

        (self.test_path / "test.md").write_text(content, encoding="utf-8")
        script_path = str(
            Path(__file__).resolve().parent.parent / "scripts" / "validate_gemini_md.py"
        )

        res_pos = subprocess.run([sys.executable, script_path, str(self.test_path / "test.md")])
        self.assertEqual(res_pos.returncode, 0)

        res_context = subprocess.run(
            [sys.executable, script_path, "--context-file", str(self.test_path / "test.md")]
        )
        self.assertEqual(res_context.returncode, 0)

        res_file = subprocess.run(
            [sys.executable, script_path, "--file", str(self.test_path / "test.md")]
        )
        self.assertEqual(res_file.returncode, 0)


if __name__ == "__main__":
    unittest.main()
