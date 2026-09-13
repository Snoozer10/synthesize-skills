"""Pressure tests for .agents/skills/release-sync/scripts/{check,bump}.py — stdlib only.

Run: python tests/test_release_sync_pressure.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "release-sync"
CHECK_PY = SKILL_DIR / "scripts" / "check.py"
BUMP_PY = SKILL_DIR / "scripts" / "bump.py"


def _run(cwd: Path, script: Path, args=None):
    cmd = [sys.executable, str(script)] + list(args or [])
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, shell=False)


def _git(cwd: Path, args):
    return subprocess.run(["git"] + list(args), cwd=str(cwd), capture_output=True, text=True, shell=False)


def _setup(tmp: Path, version="1.0.0"):
    """Minimal repo: VERSION, GEMINI.md (matching), package.json, validate.py stub, one dummy skill."""
    (tmp / "VERSION").write_text(version + "\n", encoding="utf-8")
    gemini = f'''---
project_name: "test"
version: "{version}"
tech_stack:
  - "python"
rules:
  - "stdlib-only"
exclude_paths:
  - ".git"
  - "__pycache__"
last_indexed: "2026-09-13"
generator: "test"
---
# Test
Minimal.
'''
    (tmp / "GEMINI.md").write_text(gemini, encoding="utf-8")
    pkg = f'{{"name":"test","version":"{version}"}}\n'
    (tmp / "package.json").write_text(pkg, encoding="utf-8")
    # validate.py stub (always passes)
    scripts = tmp / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "validate.py").write_text(
        'import sys\nprint("PASS")\nsys.exit(0)\n', encoding="utf-8"
    )
    # dummy skill so validate.py finds something
    skill_dir = tmp / ".agents" / "skills" / "dummy"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        '---\nname: dummy\n---\n# Dummy\n\n```bash\necho ok\n```\n',
        encoding="utf-8",
    )
    # git init
    _git(tmp, ["init"])
    _git(tmp, ["config", "user.email", "test@test.local"])
    _git(tmp, ["config", "user.name", "Test"])
    _git(tmp, ["add", "."])
    _git(tmp, ["commit", "-m", "init"])


def test_version_drift_detected():
    """VERSION != GEMINI.md version must exit 1 with 'version drift'."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _setup(tmp, "1.0.0")
        # break parity
        (tmp / "VERSION").write_text("2.0.0\n", encoding="utf-8")
        res = _run(tmp, CHECK_PY, ["--json"])
        txt = res.stdout + res.stderr
        assert res.returncode == 1, f"expected exit 1, got {res.returncode} stdout={res.stdout!r} stderr={res.stderr!r}"
        assert "version drift" in txt.lower() or "drift" in txt.lower(), f"expected 'version drift', got {txt!r}"


def test_bump_requires_apply():
    """bump.py patch without --apply must exit 0 and say 'would bump'."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _setup(tmp, "1.0.0")
        res = _run(tmp, BUMP_PY, ["patch"])
        txt = res.stdout + res.stderr
        assert res.returncode == 0, f"expected exit 0, got {res.returncode} stdout={res.stdout!r} stderr={res.stderr!r}"
        assert "would bump" in txt.lower(), f"expected 'would bump', got {txt!r}"
        # must not mutate
        assert (tmp / "VERSION").read_text(encoding="utf-8").strip() == "1.0.0", "VERSION mutated on dry-run"


if __name__ == "__main__":
    failed = 0
    for name, fn in [
        ("test_version_drift_detected", test_version_drift_detected),
        ("test_bump_requires_apply", test_bump_requires_apply),
    ]:
        try:
            fn()
            print(f"PASS: {name}")
        except AssertionError as e:
            print(f"FAIL: {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"FAIL: {name}: {e}")
            failed += 1
    sys.exit(1 if failed else 0)
