"""Test concurrency lock, atomic rollback, and bytecode exclusion for universal installer. Stdlib only.

Run: python tests/test_installer_concurrency_rollback.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_PS1 = REPO_ROOT / "install.ps1"
INSTALL_SH = REPO_ROOT / "install.sh"
BASH_EXE = Path(r"C:\Users\Snoozer\AppData\Local\hermes\git\bin\bash.exe")


def test_installer_receipt_and_rollback():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        
        # Set up a fake project root with .agents/skills/dummy/SKILL.md
        skill_dir = tmp / ".agents" / "skills" / "dummy"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("---\nname: dummy\n---\n# Dummy\n", encoding="utf-8")
        
        # Add a mock .pyc file in __pycache__ that should be excluded
        pycache = skill_dir / "__pycache__"
        pycache.mkdir(parents=True, exist_ok=True)
        (pycache / "dummy.pyc").write_bytes(b"PYC_BYTECODE")
        
        # Copy install.ps1 to temp project
        shutil_install = tmp / "install.ps1"
        shutil_install.write_text(INSTALL_PS1.read_text(encoding="utf-8"), encoding="utf-8")
        
        # Pre-existing file that will be overwritten and backed up
        claude_dir = tmp / ".claude" / "skills" / "dummy"
        claude_dir.mkdir(parents=True, exist_ok=True)
        orig_file = claude_dir / "SKILL.md"
        orig_file.write_text("ORIGINAL CONTENT", encoding="utf-8")
        
        # Run install -Force
        res = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(shutil_install), "-Force", "-Target", "claude"],
            cwd=str(tmp),
            capture_output=True,
            text=True
        )
        assert res.returncode == 0, f"Install failed: {res.stderr}"
        
        # Verify .pyc file was NOT copied
        installed_pyc = claude_dir / "__pycache__" / "dummy.pyc"
        assert not installed_pyc.exists(), "Bytecode files (*.pyc) must not be installed"
        
        # Check that receipt exists
        receipt_file = tmp / ".runtime" / "installed_receipt.json"
        assert receipt_file.is_file(), "installed_receipt.json must be generated"
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
        assert len(receipt.get("installed", [])) > 0, "Receipt must list installed files"
        assert len(receipt.get("backups", [])) > 0, "Receipt must list backup files"
        
        # Content changed to new skill
        assert "Dummy" in orig_file.read_text(encoding="utf-8")
        
        # Now run rollback
        rb_res = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(shutil_install), "-Rollback"],
            cwd=str(tmp),
            capture_output=True,
            text=True
        )
        assert rb_res.returncode == 0, f"Rollback failed: {rb_res.stderr}"
        assert "ROLLBACK COMPLETE" in rb_res.stdout
        
        # Content restored to ORIGINAL CONTENT
        assert orig_file.read_text(encoding="utf-8") == "ORIGINAL CONTENT", "Rollback must restore original content"


def test_posix_installer_receipt_and_rollback():
    if not BASH_EXE.exists():
        print("SKIP: bash not found for posix test")
        return

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        
        # Set up a fake project root with .agents/skills/dummy/SKILL.md
        skill_dir = tmp / ".agents" / "skills" / "dummy"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("---\nname: dummy\n---\n# Dummy\n", encoding="utf-8")
        
        # Add mock bytecode
        pycache = skill_dir / "__pycache__"
        pycache.mkdir(parents=True, exist_ok=True)
        (pycache / "dummy.pyc").write_bytes(b"PYC_BYTECODE")
        
        shutil_install_sh = tmp / "install.sh"
        shutil_install_sh.write_text(INSTALL_SH.read_text(encoding="utf-8"), encoding="utf-8")
        
        claude_dir = tmp / ".claude" / "skills" / "dummy"
        claude_dir.mkdir(parents=True, exist_ok=True)
        orig_file = claude_dir / "SKILL.md"
        orig_file.write_text("ORIGINAL CONTENT", encoding="utf-8")
        
        # Run posix install --force
        res = subprocess.run(
            [str(BASH_EXE), "./install.sh", "--force", "--target", "claude"],
            cwd=str(tmp),
            capture_output=True,
            text=True
        )
        assert res.returncode == 0, f"POSIX install failed: {res.stderr} {res.stdout}"
        
        # Verify .pyc file was NOT copied
        installed_pyc = claude_dir / "__pycache__" / "dummy.pyc"
        assert not installed_pyc.exists(), "POSIX: Bytecode files (*.pyc) must not be installed"
        
        # Check receipt exists
        receipt_file = tmp / ".runtime" / "installed_receipt.json"
        assert receipt_file.is_file(), "POSIX: installed_receipt.json must be generated"
        
        # Test posix rollback
        rb_res = subprocess.run(
            [str(BASH_EXE), "./install.sh", "--rollback"],
            cwd=str(tmp),
            capture_output=True,
            text=True
        )
        assert rb_res.returncode == 0, f"POSIX rollback failed: {rb_res.stderr} {rb_res.stdout}"
        assert "ROLLBACK COMPLETE" in rb_res.stdout
        assert orig_file.read_text(encoding="utf-8") == "ORIGINAL CONTENT"


if __name__ == "__main__":
    tests = [
        ("test_installer_receipt_and_rollback", test_installer_receipt_and_rollback),
        ("test_posix_installer_receipt_and_rollback", test_posix_installer_receipt_and_rollback),
    ]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS: {name}")
        except Exception as e:
            print(f"FAIL: {name}: {e}")
            failed += 1
    sys.exit(1 if failed else 0)
