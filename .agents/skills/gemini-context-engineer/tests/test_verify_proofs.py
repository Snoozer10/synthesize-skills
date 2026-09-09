import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

# Add scripts to sys.path so we can import verify_proofs
TEST_DIR = pathlib.Path(__file__).parent.absolute()
SKILL_DIR = TEST_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import verify_proofs
except ImportError:
    pass


class TestVerifyProofs(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = pathlib.Path(self.temp_dir.name)
        self.gemini_md = self.temp_path / "GEMINI.md"
        self.gemini_md.write_text(self._get_sample_gemini_md(), encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _get_sample_gemini_md(self):
        return """
# Project Context

## Active Workstreams & Verification Status
| ID | Workstream Slice | Status | Blocked By | Proof Command |
| :--- | :--- | :--- | :--- | :--- |
| `#1` | Task 1 | In Progress | - | python -c "import sys; sys.exit(0)" |
| `#2` | Task 2 | Pending | `#1` | python -c "print('ok')" |
| `#3` | Task 3 | Done | - | echo "done" |
"""

    def test_parse_table_and_dag(self):
        content = self._get_sample_gemini_md()
        tasks = verify_proofs.parse_table_and_dag(content)
        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks["#1"]["status"], "In Progress")
        self.assertEqual(tasks["#1"]["blocked_by"], [])
        self.assertEqual(tasks["#1"]["proof_command"], 'python -c "import sys; sys.exit(0)"')
        self.assertEqual(tasks["#2"]["blocked_by"], ["#1"])

    def test_blocked_dependency_rejection(self):
        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "verify_proofs.py"),
            "--workstream",
            "#2",
            "--file",
            str(self.gemini_md),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 1)
        self.assertIn("ERR_DEPENDENCY_BLOCKED", result.stderr)

    def test_failing_proof_rejection(self):
        failing_md = self._get_sample_gemini_md().replace(
            'python -c "import sys; sys.exit(0)"', 'python -c "import sys; sys.exit(1)"'
        )
        self.gemini_md.write_text(failing_md, encoding="utf-8")
        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "verify_proofs.py"),
            "--workstream",
            "#1",
            "--file",
            str(self.gemini_md),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 1)
        self.assertIn("ERR_PROOF_FAILED", result.stderr)

        content = self.gemini_md.read_text(encoding="utf-8")
        self.assertIn("| `#1` | Task 1 | In Progress | - | python -c", content)

    def test_passing_proof_and_transition(self):
        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "verify_proofs.py"),
            "--workstream",
            "#1",
            "--file",
            str(self.gemini_md),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0)

        content = self.gemini_md.read_text(encoding="utf-8")
        self.assertIn("| `#1` | Task 1 | Done | - |", content)
        self.assertIn("unlocked", result.stdout.lower())

    def test_check_only_flag(self):
        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "verify_proofs.py"),
            "--workstream",
            "#1",
            "--file",
            str(self.gemini_md),
            "--check-only",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0)

        content = self.gemini_md.read_text(encoding="utf-8")
        self.assertIn("| `#1` | Task 1 | In Progress | - |", content)

    def test_cli_json_output(self):
        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "verify_proofs.py"),
            "--json",
            "--file",
            str(self.gemini_md),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIn("#1", data)
        self.assertEqual(data["#1"]["status"], "In Progress")
        self.assertEqual(data["#2"]["blocked_by"], ["#1"])

    def test_context_file_alias(self):
        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "verify_proofs.py"),
            "--json",
            "--context-file",
            str(self.gemini_md),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0)

    def test_proof_timeout(self):
        timeout_md = self._get_sample_gemini_md().replace(
            'python -c "import sys; sys.exit(0)"', 'python -c "import time; time.sleep(10)"'
        )
        self.gemini_md.write_text(timeout_md, encoding="utf-8")
        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "verify_proofs.py"),
            "--workstream",
            "#1",
            "--file",
            str(self.gemini_md),
            "--timeout",
            "1",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 1)
        self.assertIn("ERR_PROOF_TIMEOUT", result.stderr)


if __name__ == "__main__":
    unittest.main()
