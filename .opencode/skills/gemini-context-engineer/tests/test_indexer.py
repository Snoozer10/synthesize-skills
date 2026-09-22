import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Add parent directory to sys.path to import indexer
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.repo_indexer import (
    fallback_walk,
    index_repository,
    is_dangerous_root,
    parse_manifests,
    run_git_ls_files,
)


class TestIndexer(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_path = Path(self.test_dir.name).resolve()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_git_ls_files_fast_path(self):
        subprocess.run(["git", "init"], cwd=self.test_path, capture_output=True)
        (self.test_path / "test.txt").touch()
        subprocess.run(["git", "add", "test.txt"], cwd=self.test_path, capture_output=True)

        files = run_git_ls_files(self.test_path)
        self.assertIsNotNone(files)
        self.assertIn("test.txt", [f.name for f in files])

        res = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent.parent / "scripts" / "repo_indexer.py"),
                "--root",
                str(self.test_path),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        data = json.loads(res.stdout)
        self.assertEqual(data["traversal_engine"], "git")
        self.assertEqual(data["file_count"], 1)

    def test_fallback_traversal(self):
        (self.test_path / "test2.txt").touch()
        files = fallback_walk(self.test_path, 3)
        self.assertIn("test2.txt", [f.name for f in files])

        res = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent.parent / "scripts" / "repo_indexer.py"),
                "--root",
                str(self.test_path),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        data = json.loads(res.stdout)
        self.assertEqual(data["traversal_engine"], "walk")
        self.assertEqual(data["file_count"], 1)

    def test_directory_traversal_excludes(self):
        excludes = [".git", "node_modules", "venv", "dist", "__pycache__"]
        for exc in excludes:
            exc_path = self.test_path / exc
            exc_path.mkdir()
            (exc_path / "ignored.txt").touch()

        (self.test_path / "included.txt").touch()

        files = fallback_walk(self.test_path, 3)
        names = [f.name for f in files]
        self.assertNotIn("ignored.txt", names)
        self.assertIn("included.txt", names)

    def test_home_directory_safety_guard(self):
        home = Path.home()
        self.assertTrue(is_dangerous_root(home))

        res2 = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent.parent / "scripts" / "repo_indexer.py"),
                "--root",
                str(home),
                "--scope",
                "global",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res2.returncode, 1)
        self.assertIn("error", json.loads(res2.stdout))

    def test_manifest_parsing(self):
        manifests = {
            "package.json": '{"name": "test-node"}',
            "pyproject.toml": '[tool.poetry]\nname = "test-py"',
            "Cargo.toml": '[package]\nname = "test-rs"',
            "go.mod": "module test-go\n",
        }
        for name, content in manifests.items():
            (self.test_path / name).write_text(content, encoding="utf-8")

        files = [self.test_path / name for name in manifests.keys()]
        parsed = parse_manifests(files, self.test_path)

        self.assertEqual(parsed["node"]["name"], "test-node")
        self.assertEqual(parsed["python"]["poetry"]["name"], "test-py")
        self.assertEqual(parsed["rust"]["package"]["name"], "test-rs")
        self.assertEqual(parsed["go"]["module"], "test-go")

    def test_json_output_and_version_flag(self):
        res = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent.parent / "scripts" / "repo_indexer.py"),
                "--version",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)

        (self.test_path / "test3.txt").touch()
        res2 = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent.parent / "scripts" / "repo_indexer.py"),
                "--root",
                str(self.test_path),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        data = json.loads(res2.stdout)
        self.assertIn("file_count", data)
        self.assertIn("traversal_engine", data)

    def test_subtree_gemini_discovery(self):
        sub_dir = self.test_path / "sub"
        sub_dir.mkdir()
        (sub_dir / "GEMINI.md").touch()

        res = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent.parent / "scripts" / "repo_indexer.py"),
                "--root",
                str(self.test_path),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        data = json.loads(res.stdout)
        child_contexts = data.get("child_contexts", [])
        self.assertEqual(len(child_contexts), 1)
        self.assertIn("path", child_contexts[0])
        self.assertEqual(child_contexts[0]["scope"], "sub")

    def test_cross_ecosystem_manifest_scanner(self):
        (self.test_path / "CLAUDE.md").write_text(
            "<!-- AGENT-SYNC: GEMINI.md -->", encoding="utf-8"
        )
        (self.test_path / "AGENTS.md").write_text(
            "Divergent content without reference", encoding="utf-8"
        )

        res = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent.parent / "scripts" / "repo_indexer.py"),
                "--root",
                str(self.test_path),
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        data = json.loads(res.stdout)
        federation = data.get("federation", {})
        self.assertEqual(federation.get("CLAUDE.md"), "pointer_shim")
        self.assertEqual(federation.get("AGENTS.md"), "divergent")
        self.assertEqual(federation.get(".cursorrules"), "missing")

    def test_federate_flag(self):
        (self.test_path / "GEMINI.md").touch()
        res = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent.parent / "scripts" / "repo_indexer.py"),
                "--root",
                str(self.test_path),
                "--federate",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)

        self.assertTrue((self.test_path / "CLAUDE.md").exists())
        self.assertTrue((self.test_path / "AGENTS.md").exists())
        self.assertTrue((self.test_path / ".cursorrules").exists())

        for fname in ["CLAUDE.md", "AGENTS.md", ".cursorrules"]:
            fpath = self.test_path / fname
            if not fpath.is_symlink():
                self.assertIn("<!-- AGENT-SYNC: GEMINI.md -->", fpath.read_text(encoding="utf-8"))

    def test_ast_leverage_deep_and_shallow_modules(self):
        modules_dir = self.test_path / "src" / "modules"
        modules_dir.mkdir(parents=True, exist_ok=True)
        deep_py = modules_dir / "deep_service.py"
        shallow_py = modules_dir / "shallow_adapter.py"

        deep_py.write_text("def interface_function():\n" + "    pass\n" * 35, encoding="utf-8")

        shallow_py.write_text(
            "def f1(a, b, c, d, e):\n    return a + b\n"
            "def f2(a, b, c, d, e):\n    return a + b\n"
            "def f3(a, b, c, d, e):\n    return a + b\n"
            "def f4(a, b, c, d, e):\n    return a + b\n",
            encoding="utf-8",
        )

        res = index_repository(self.test_path)
        arch = res.get("architectural_health", {})

        deep_paths = [Path(m["path"]).name for m in arch.get("deep_modules", [])]
        shallow_paths = [Path(m["path"]).name for m in arch.get("shallow_modules", [])]

        self.assertIn("deep_service.py", deep_paths)
        self.assertIn("shallow_adapter.py", shallow_paths)

    def test_ast_syntax_error_resilience(self):
        bad_py = self.test_path / "bad.py"
        bad_py.write_text("def broken(\n", encoding="utf-8")

        # Should not raise exception
        res = index_repository(self.test_path)
        self.assertIsInstance(res, dict)


if __name__ == "__main__":
    unittest.main()
