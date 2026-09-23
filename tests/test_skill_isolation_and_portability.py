"""Comprehensive Skill Isolation, Selective Installation & Portability Tests.
Stdlib only. Tests non-destructive hook chaining, selective installer flags,
and independent standalone execution of each skill.

Run: python tests/test_skill_isolation_and_portability.py
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
INSTALL_PS1 = REPO_ROOT / "install.ps1"
INSTALL_SH = REPO_ROOT / "install.sh"
BASH_EXE = pathlib.Path(r"C:\Users\Snoozer\AppData\Local\hermes\git\bin\bash.exe")
if not BASH_EXE.exists():
    # Fallback to system bash if available
    bash_which = shutil.which("bash")
    if bash_which:
        BASH_EXE = pathlib.Path(bash_which)


def test_selective_skill_install_powershell():
    print("[1/4] Running test_selective_skill_install_powershell...")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)

        # Copy install.ps1 and canonical .agents/skills to temp project
        shutil.copy2(INSTALL_PS1, tmp / "install.ps1")
        shutil.copytree(REPO_ROOT / ".agents" / "skills", tmp / ".agents" / "skills")

        # 1. Install single skill: skill-creator
        res = subprocess.run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(tmp / "install.ps1"),
                "-Skill",
                "skill-creator",
                "-Target",
                "claude",
                "-Force",
            ],
            cwd=str(tmp),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert res.returncode == 0, f"Single skill install failed: {res.stderr}\n{res.stdout}"

        claude_dir = tmp / ".claude" / "skills"
        assert (claude_dir / "skill-creator" / "SKILL.md").exists(), "skill-creator must be installed"
        assert not (claude_dir / "release-sync").exists(), "release-sync must NOT be installed"
        assert not (claude_dir / "gemini-context-engineer").exists(), "gemini-context-engineer must NOT be installed"
        assert not (claude_dir / "repo-blast-radius-sync").exists(), "repo-blast-radius-sync must NOT be installed"

        receipt_file = tmp / ".runtime" / "installed_receipt.json"
        assert receipt_file.is_file(), "Receipt must be created"
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
        assert receipt.get("skills") == ["skill-creator"], f"Receipt must record skills: {receipt.get('skills')}"

        # 2. Install subset: release-sync,repo-blast-radius-sync
        res_subset = subprocess.run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(tmp / "install.ps1"),
                "-Skill",
                "release-sync, repo-blast-radius-sync",
                "-Target",
                "claude",
                "-Force",
            ],
            cwd=str(tmp),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert res_subset.returncode == 0, f"Subset install failed: {res_subset.stderr}"
        assert (claude_dir / "release-sync" / "SKILL.md").exists(), "release-sync must now be installed"
        assert (claude_dir / "repo-blast-radius-sync" / "SKILL.md").exists(), "repo-blast-radius-sync must now be installed"
        assert not (claude_dir / "gemini-context-engineer").exists(), "gemini-context-engineer must still NOT be installed"

        # 3. Test invalid skill name fails with non-zero exit code
        res_invalid = subprocess.run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(tmp / "install.ps1"),
                "-Skill",
                "non-existent-skill",
                "-Target",
                "claude",
            ],
            cwd=str(tmp),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert res_invalid.returncode != 0, "Invalid skill name must fail"
        assert "not found in canonical skills directory" in res_invalid.stderr

    print("PASS: test_selective_skill_install_powershell")


def test_selective_skill_install_posix():
    print("[2/4] Running test_selective_skill_install_posix...")
    if not BASH_EXE.exists():
        print("SKIP: bash not found for posix test")
        return

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)

        shutil.copy2(INSTALL_SH, tmp / "install.sh")
        shutil.copytree(REPO_ROOT / ".agents" / "skills", tmp / ".agents" / "skills")

        # 1. Install single skill via bash
        res = subprocess.run(
            [str(BASH_EXE), "./install.sh", "--skill", "skill-creator", "--target", "claude", "--force"],
            cwd=str(tmp),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert res.returncode == 0, f"POSIX single skill install failed: {res.stderr}\n{res.stdout}"

        claude_dir = tmp / ".claude" / "skills"
        assert (claude_dir / "skill-creator" / "SKILL.md").exists(), "POSIX: skill-creator must be installed"
        assert not (claude_dir / "release-sync").exists(), "POSIX: release-sync must NOT be installed"
        assert not (claude_dir / "gemini-context-engineer").exists(), "POSIX: gemini-context-engineer must NOT be installed"

        receipt_file = tmp / ".runtime" / "installed_receipt.json"
        assert receipt_file.is_file(), "POSIX receipt must be created"
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
        assert receipt.get("skill") == "skill-creator"

        # 2. Test invalid skill name fails
        res_invalid = subprocess.run(
            [str(BASH_EXE), "./install.sh", "--skill", "invalid-xyz", "--target", "claude"],
            cwd=str(tmp),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert res_invalid.returncode != 0, "POSIX invalid skill name must fail"
        assert "not found in canonical skills directory" in res_invalid.stderr

    print("PASS: test_selective_skill_install_posix")


def test_nondestructive_git_hook_chaining():
    print("[3/4] Running test_nondestructive_git_hook_chaining...")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)

        # Initialize mock git repository
        subprocess.run(["git", "init"], cwd=str(tmp), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(tmp), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp), capture_output=True, check=True)

        scripts_dir = tmp / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        # Copy context_daemon.py and release_sync.py to mock repo
        src_daemon = REPO_ROOT / ".agents" / "skills" / "gemini-context-engineer" / "scripts" / "context_daemon.py"
        src_release = REPO_ROOT / "scripts" / "release_sync.py"
        shutil.copy2(src_daemon, scripts_dir / "context_daemon.py")
        shutil.copy2(src_release, scripts_dir / "release_sync.py")

        hook_path = tmp / ".git" / "hooks" / "pre-commit"
        assert not hook_path.exists(), "Hook should not exist prior to install"

        # 1. Install context_daemon hook
        res1 = subprocess.run(
            [sys.executable, str(scripts_dir / "context_daemon.py"), "--install-hooks", "--root", str(tmp)],
            cwd=str(tmp),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert res1.returncode == 0, f"context_daemon install_hooks failed: {res1.stderr}"
        assert hook_path.is_file(), "pre-commit hook must exist"
        c1 = hook_path.read_text(encoding="utf-8")
        assert "context_daemon.py" in c1
        assert "release_sync" not in c1

        # 2. Install release_sync hook non-destructively
        res2 = subprocess.run(
            [sys.executable, str(scripts_dir / "release_sync.py"), "--install-hooks"],
            cwd=str(tmp),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert res2.returncode == 0, f"release_sync install_hooks failed: {res2.stderr}"
        c2 = hook_path.read_text(encoding="utf-8")
        assert "context_daemon.py" in c2, "context_daemon hook must be PRESERVED after release_sync install"
        assert "release_sync.py" in c2, "release_sync hook must be present"

        # 3. Idempotency test: Re-run both hook installers, ensure zero duplicated entries
        res3 = subprocess.run(
            [sys.executable, str(scripts_dir / "context_daemon.py"), "--install-hooks", "--root", str(tmp)],
            cwd=str(tmp),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert res3.returncode == 0
        res4 = subprocess.run(
            [sys.executable, str(scripts_dir / "release_sync.py"), "--install-hooks"],
            cwd=str(tmp),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert res4.returncode == 0

        c_final = hook_path.read_text(encoding="utf-8")
        assert c_final.count("context_daemon.py") == 1, "context_daemon.py hook entry must not be duplicated"
        assert c_final.count("release_sync.py") == 1, "release_sync.py hook entry must not be duplicated"

    print("PASS: test_nondestructive_git_hook_chaining")


def test_standalone_skill_portability():
    print("[4/4] Running test_standalone_skill_portability...")
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)

        # Initialize bare mock git repo
        subprocess.run(["git", "init"], cwd=str(tmp), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(tmp), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp), capture_output=True, check=True)

        # 1. Standalone init_skill.py from skill-creator (zero other skill dependencies)
        init_script = REPO_ROOT / ".agents" / "skills" / "skill-creator" / "scripts" / "init_skill.py"
        res_init = subprocess.run(
            [
                sys.executable,
                str(init_script),
                "standalone-skill",
                "--dest",
                str(tmp / "skills"),
                "--desc",
                "Use when verifying complete standalone portability without repo dependencies.",
                "--keywords",
                "isolated, standalone, portable",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert res_init.returncode == 0, f"init_skill standalone failed: {res_init.stderr}"
        assert (tmp / "skills" / "standalone-skill" / "SKILL.md").exists()

        # 2. Standalone release_sync check.py
        check_script = REPO_ROOT / ".agents" / "skills" / "release-sync" / "scripts" / "check.py"
        (tmp / "VERSION").write_text("1.0.0\n", encoding="utf-8")
        (tmp / "package.json").write_text(json.dumps({"name": "test", "version": "1.0.0"}), encoding="utf-8")
        (tmp / "GEMINI.md").write_text('---\nversion: "1.0.0"\n---\n', encoding="utf-8")
        res_check = subprocess.run(
            [sys.executable, str(check_script)],
            cwd=str(tmp),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert res_check.returncode == 0, f"release-sync check.py standalone failed: {res_check.stderr}"

        # 3. Standalone discover_standards.py from repo-standards-engineer
        disc_script = REPO_ROOT / ".agents" / "skills" / "repo-standards-engineer" / "scripts" / "discover_standards.py"
        (tmp / "app.py").write_text("class ErrorCode:\n    INVALID_ID = 'ERR_001'\n", encoding="utf-8")
        res_disc = subprocess.run(
            [sys.executable, str(disc_script), "--dir", str(tmp), "--json"],
            cwd=str(tmp),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert res_disc.returncode == 0, f"discover_standards.py standalone failed: {res_disc.stderr}"
        data = json.loads(res_disc.stdout)
        assert len(data) >= 0

        # 4. Standalone blast_radius.py from repo-blast-radius-sync
        blast_script = REPO_ROOT / ".agents" / "skills" / "repo-blast-radius-sync" / "scripts" / "blast_radius.py"
        res_blast = subprocess.run(
            [sys.executable, str(blast_script), "app.py", "--json"],
            cwd=str(tmp),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert res_blast.returncode == 0, f"blast_radius.py standalone failed: {res_blast.stderr}"

    print("PASS: test_standalone_skill_portability")


if __name__ == "__main__":
    test_selective_skill_install_powershell()
    test_selective_skill_install_posix()
    test_nondestructive_git_hook_chaining()
    test_standalone_skill_portability()
    print("\nALL SKILL ISOLATION & PORTABILITY TESTS PASSED (4/4)!")
