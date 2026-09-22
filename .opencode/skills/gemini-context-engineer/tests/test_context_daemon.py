import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

try:
    import context_daemon
except ImportError:
    context_daemon = None


class TestContextDaemon(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_dir = Path(self.temp_dir.name)

        # Initialize a synthetic git repo
        subprocess.run(["git", "init"], cwd=self.repo_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=self.repo_dir,
            check=True,
            capture_output=True,
        )

        self.original_cwd = os.getcwd()
        os.chdir(self.repo_dir)

        self.daemon_script = SKILL_ROOT / "scripts" / "context_daemon.py"

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()

    def test_staged_files_detection(self):
        if context_daemon is None:
            self.skipTest("context_daemon module not found")

        foo_py = self.repo_dir / "foo.py"
        foo_py.write_text("print('hello')\n", encoding="utf-8")
        subprocess.run(["git", "add", "foo.py"], cwd=self.repo_dir, check=True)

        staged = context_daemon.get_staged_or_changed_files(self.repo_dir, mode="pre-commit")
        self.assertIn(self.repo_dir / "foo.py", staged)

    def test_contract_break_detection(self):
        # Create calc.py with `def add(a, b): pass`
        calc_py = self.repo_dir / "calc.py"
        calc_py.write_text("def add(a, b):\n    pass\n", encoding="utf-8")
        subprocess.run(["git", "add", "calc.py"], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.repo_dir, check=True)

        # Modify calc.py to `def add(a, b, c): pass`
        calc_py.write_text("def add(a, b, c):\n    pass\n", encoding="utf-8")
        subprocess.run(["git", "add", "calc.py"], cwd=self.repo_dir, check=True)

        result = subprocess.run(
            [sys.executable, str(self.daemon_script), "--mode", "pre-commit"],
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            "Signature changes detected" in result.stdout
            or "Signature changes detected" in result.stderr
        )
        self.assertTrue(
            "Signature changed for add" in result.stdout
            or "Signature changed for add" in result.stderr
        )

    def test_reality_drift_detection(self):
        gemini_md = self.repo_dir / "GEMINI.md"
        gemini_md.write_text(
            "## 🏗️ Architecture & Component Mapping\n"
            "| Component | File |\n"
            "|---|---|\n"
            "| [service.py](service.py) | desc |\n",
            encoding="utf-8",
        )

        service_py = self.repo_dir / "service.py"
        service_py.write_text("def serve(): pass\n", encoding="utf-8")

        subprocess.run(["git", "add", "GEMINI.md", "service.py"], cwd=self.repo_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add GEMINI.md and service.py"], cwd=self.repo_dir, check=True
        )

        # Remove service.py
        subprocess.run(["git", "rm", "service.py"], cwd=self.repo_dir, check=True)

        result = subprocess.run(
            [sys.executable, str(self.daemon_script), "--mode", "pre-commit"],
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 1, "Expected daemon to fail due to reality drift")
        output = result.stdout + result.stderr
        self.assertTrue("Reality drift detected" in output)
        self.assertTrue("Missing referenced file from disk: service.py" in output)

    def test_auto_patch_mode(self):
        # Create a repo state that will trigger an error (e.g. signature change)
        gemini_md = self.repo_dir / "GEMINI.md"
        gemini_md.write_text(
            'last_indexed: "2020-01-01"\n'
            "### Architectural Health & Deep Modules\n"
            "| Module / Subtree | Interface Count | Implementation LOC | Leverage | Classification |\n"
            "| :--- | :--- | :--- | :--- | :--- |\n"
            "| [old.py](old.py) | 0 | 0 | 0.0 | Deep Module |\n"
            "\n",
            encoding="utf-8",
        )

        calc_py = self.repo_dir / "calc.py"
        calc_py.write_text("def calc(a, b):\n    pass\n", encoding="utf-8")

        subprocess.run(["git", "add", "GEMINI.md", "calc.py"], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=self.repo_dir, check=True)

        # Modify calc.py to trigger signature change
        calc_py.write_text("def calc(a, b, c):\n    pass\n", encoding="utf-8")
        subprocess.run(["git", "add", "calc.py"], cwd=self.repo_dir, check=True)

        result = subprocess.run(
            [sys.executable, str(self.daemon_script), "--mode", "pre-commit", "--auto-patch"],
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
        )

        # It should exit 0 because auto-patch fixed it
        self.assertEqual(
            result.returncode, 0, f"Auto-patch failed: {result.stderr}\n{result.stdout}"
        )

        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=self.repo_dir, capture_output=True, text=True
        ).stdout
        self.assertTrue(
            any(line.endswith("GEMINI.md") for line in status.splitlines()),
            f"GEMINI.md not modified. Status:\n{status}\nDaemon Output:\n{result.stdout}\nDaemon Error:\n{result.stderr}",
        )

    def test_install_hooks(self):
        result = subprocess.run(
            [sys.executable, str(self.daemon_script), "--install-hooks"],
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, f"Hook installation failed: {result.stderr}")

        hook_path = self.repo_dir / ".git" / "hooks" / "pre-commit"
        self.assertTrue(hook_path.exists(), "pre-commit hook was not created")

        # Check executable permission
        self.assertTrue(os.access(hook_path, os.X_OK), "pre-commit hook is not executable")

    def test_file_alias_and_empty_diff(self):
        result = subprocess.run(
            [sys.executable, str(self.daemon_script), "--file", "GEMINI.md"],
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
