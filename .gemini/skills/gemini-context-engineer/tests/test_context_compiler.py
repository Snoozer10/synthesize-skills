import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

# Add scripts directory to path to import context_compiler
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
import context_compiler


class TestContextCompiler(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = pathlib.Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_ast_dependency_closure(self):
        # Create synthetic modules
        a_py = self.temp_path / "a.py"
        b_py = self.temp_path / "b.py"
        c_py = self.temp_path / "c.py"

        a_py.write_text("import b\ndef func_a():\n    pass\n", encoding="utf-8")
        b_py.write_text("import c\ndef func_b():\n    c.func_c()\n", encoding="utf-8")
        c_py.write_text("def func_c():\n    pass\n", encoding="utf-8")

        # We use analyze_file which acts as the dependency subgraph builder
        # Note: aliased to conceptually match "build_dependency_subgraph"
        visited = set()
        graph_files, symbols = context_compiler.analyze_file(self.temp_path, a_py, visited)

        self.assertIn("a.py", graph_files)
        self.assertIn("b.py", graph_files)
        self.assertIn("c.py", graph_files)

        self.assertIn("func_a", symbols)
        self.assertIn("func_b", symbols)
        self.assertIn("func_c", symbols)

    def test_syntax_error_resilience(self):
        broken_py = self.temp_path / "broken.py"
        broken_py.write_text("def broken_func(:\n    pass\n", encoding="utf-8")

        visited = set()
        graph_files, symbols = context_compiler.analyze_file(self.temp_path, broken_py, visited)

        self.assertIn("broken.py", graph_files)
        self.assertIn("broken_func", symbols)

    def test_context_slicing_and_keywords(self):
        gemini_md = self.temp_path / "GEMINI.md"
        gemini_md.write_text(
            """---
title: Project Context
---
# Context
## Architecture & Component Mapping
| Component | File Path | Responsibility |
| :--- | :--- | :--- |
| Audio | audio.py | Audio component |
| Video | video.py | Video component |
| Translation | translate.py | Translation component |

## Mandatory Engineering Constraints
- Anti-Sycophancy: Always be honest.
- Always append format=nv12 to h264_qsv filters.
- Audio constraint on LUFS.
""",
            encoding="utf-8",
        )

        video_py = self.temp_path / "video.py"
        video_py.write_text("def video_func(): pass", encoding="utf-8")

        final_md, metadata = context_compiler.compile_context(
            root_path=self.temp_path,
            files=["video.py"],
            task="Fix NV12 QSV filtergraph",
            budget=2000,
            context_file=gemini_md,
        )

        # Assert video components and invariants are retained
        self.assertIn("Video component", final_md)
        self.assertIn("Anti-Sycophancy", final_md)  # Universal
        self.assertIn("format=nv12", final_md)  # Video invariant triggered by QSV/NV12 task

        # Assert audio/translation components are pruned
        self.assertNotIn("Audio component", final_md)
        self.assertNotIn("Translation component", final_md)

    def test_budget_clamping_and_priority_pruning(self):
        gemini_md = self.temp_path / "GEMINI.md"
        # Create a document that will be pruned to fit budget
        gemini_md.write_text(
            """---
title: Big Project
---
# Context
## Architecture & Component Mapping
| Component | File Path |
| :--- | :--- |
| Core | core.py |

## Mandatory Engineering Constraints
- Anti-Sycophancy: universal truth

## Active Workstreams
| ID | Status |
| :--- | :--- |
| 1 | Done """
            + ("word " * 500)
            + """ |
""",
            encoding="utf-8",
        )

        core_py = self.temp_path / "core.py"
        core_py.write_text("def core_func(): pass", encoding="utf-8")

        # Test with tight budget
        final_md, metadata = context_compiler.compile_context(
            root_path=self.temp_path,
            files=["core.py"],
            task="Work on core",
            budget=200,
            context_file=gemini_md,
        )

        token_count = len(final_md) // 4
        self.assertLessEqual(token_count, 200)

        # Universal cognitive invariants (Anti-Sycophancy) should be preserved
        self.assertIn("Anti-Sycophancy", final_md)
        # Lower-priority sections (Workstreams) dropped
        self.assertNotIn("Active Workstreams", final_md)

    def test_cli_flags(self):
        script_path = pathlib.Path(__file__).parent.parent / "scripts" / "context_compiler.py"
        out_file = self.temp_path / "out.md"

        a_py = self.temp_path / "a.py"
        a_py.write_text("def a(): pass", encoding="utf-8")

        gemini_md = self.temp_path / "GEMINI.md"
        gemini_md.write_text("# Title\n## Architecture", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--root",
                str(self.temp_path),
                "--files",
                "a.py",
                "--task",
                "Fix NV12",
                "--budget",
                "200",
                "--out",
                str(out_file),
                "--json",
            ],
            capture_output=True,
            text=True,
            cwd=str(self.temp_path),
        )

        self.assertEqual(result.returncode, 0, f"Command failed: {result.stderr}")

        # Assert --out writes the file
        self.assertTrue(out_file.exists())

        # Assert --json prints valid JSON payload
        output_json = json.loads(result.stdout.strip())
        self.assertIn("compiled_markdown", output_json)
        self.assertIn("metadata", output_json)

    def test_file_alias_flag(self):
        script_path = pathlib.Path(__file__).parent.parent / "scripts" / "context_compiler.py"
        a_py = self.temp_path / "a.py"
        a_py.write_text("def a(): pass", encoding="utf-8")
        gemini_md = self.temp_path / "GEMINI.md"
        gemini_md.write_text("# Title\n## Architecture", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--root",
                str(self.temp_path),
                "--files",
                "a.py",
                "--task",
                "Fix NV12",
                "--file",
                str(gemini_md),
                "--json",
            ],
            capture_output=True,
            text=True,
            cwd=str(self.temp_path),
        )
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
