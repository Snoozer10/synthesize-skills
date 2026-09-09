"""Smoke tests for scripts/release_sync.py — stdlib only, hermetic.

Uses TemporaryDirectory + isolated git init repos, hashlib.sha256,
subprocess shell=False, pathlib, re, os, shutil, sys.
No pytest, no pip.

Run: python tests/test_release_sync_smoke.py
"""
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# locate repo src (where VERSION lives) — search upward from this file
def _find_repo_src():
    cur = Path(__file__).resolve().parent
    for _ in range(6):
        if (cur / "VERSION").exists() and (cur / "scripts" / "release_sync.py").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    # fallback: parent of tests/
    return Path(__file__).resolve().parents[1]

REPO_SRC = _find_repo_src()


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


def _load_release_sync():
    spec = importlib.util.spec_from_file_location(
        "release_sync", str(REPO_SRC / "scripts" / "release_sync.py")
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(mod)  # type: ignore
    return mod


_RS = _load_release_sync()


def _run_sync(cwd: Path, args):
    cmd = [sys.executable, "scripts/release_sync.py"] + list(args)
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, shell=False)


def _git(cwd: Path, args):
    return subprocess.run(["git"] + list(args), cwd=str(cwd), capture_output=True, text=True, shell=False)


def _setup_clean_repo(tmp: Path) -> Path:
    # copy canonical files
    for name in ["VERSION", "GEMINI.md", "README.md", "CHANGELOG.md"]:
        src = REPO_SRC / name
        if src.exists():
            dst = tmp / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
    # copy scripts
    for scr in ["validate.py", "release_sync.py"]:
        src = REPO_SRC / "scripts" / scr
        if src.exists():
            dst = tmp / "scripts" / scr
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
    # minimal valid skill so scripts/validate.py passes (needs at least one SKILL.md)
    dummy_dir = tmp / ".agents" / "skills" / "dummy"
    dummy_dir.mkdir(parents=True, exist_ok=True)
    dummy_content = """---
name: dummy
description: "Use when testing dummy skill Keywords: smoke dummy test"
---
# Dummy

Minimal skill for smoke tests.

```bash
echo hello
```

Keywords: smoke dummy test
"""
    (dummy_dir / "SKILL.md").write_text(dummy_content, encoding="utf-8", newline="\n")
    # git init + commit -> git diff --quiet == clean
    r = _git(tmp, ["init"])
    if r.returncode != 0:
        raise RuntimeError(f"git init failed: {r.stderr}")
    _git(tmp, ["config", "user.email", "smoke@test.local"])
    _git(tmp, ["config", "user.name", "Smoke"])
    _git(tmp, ["add", "."])
    r2 = _git(tmp, ["commit", "-m", "init"])
    if r2.returncode != 0:
        raise RuntimeError(f"git commit failed: {r2.stdout} {r2.stderr}")
    return tmp


def test_01_check_readonly_hash_proof():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _setup_clean_repo(tmp)
        files = [tmp / "VERSION", tmp / "GEMINI.md", tmp / "README.md"]
        before = {p.name: _sha256(p) for p in files}
        res = _run_sync(tmp, ["--check"])
        after = {p.name: _sha256(p) for p in files}
        assert res.returncode == 0, f"--check should exit 0 clean, got {res.returncode} stdout={res.stdout} stderr={res.stderr}"
        assert before == after, f"hash proof failed --check mutated files: before={before} after={after}"


def test_02_dirty_tree_abort():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _setup_clean_repo(tmp)
        # dirty a tracked file without committing — --check is read-only (no git_clean), --bump must abort
        # dirty README (not VERSION) to avoid version mismatch drift
        (tmp / "README.md").write_text((tmp / "README.md").read_text(encoding="utf-8") + "\ndirty\n", encoding="utf-8")
        res = _run_sync(tmp, ["--check"])
        assert res.returncode == 0, f"--check should not abort on dirty (pre-commit has staged), got {res.returncode} {res.stdout} {res.stderr}"
        res2 = _run_sync(tmp, ["--bump", "patch", "--apply"])
        assert res2.returncode == 1, f"dirty bump should abort exit 1, got {res2.returncode} {res2.stdout} {res2.stderr}"
        txt = res2.stdout + res2.stderr
        assert "working tree not clean" in txt or "drift" in txt.lower(), f"expected dirty message, got {txt!r}"


def test_03_missing_readme_markers_abort():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _setup_clean_repo(tmp)
        # remove markers and commit so tree is clean but markers missing
        readme = tmp / "README.md"
        t = readme.read_text(encoding="utf-8")
        t2 = t.replace("<!-- release-sync:start -->", "").replace("<!-- release-sync:end -->", "")
        # ensure markers gone
        assert "<!-- release-sync:start -->" not in t2
        readme.write_text(t2, encoding="utf-8", newline="\n")
        _git(tmp, ["add", "README.md"])
        _git(tmp, ["commit", "-m", "break readme"])
        res = _run_sync(tmp, ["--check"])
        assert res.returncode == 1, f"missing README markers should exit 1, got {res.returncode} {res.stdout} {res.stderr}"
        txt = res.stdout + res.stderr
        assert "release-sync" in txt.lower() or "readme" in txt.lower(), f"expected README marker drift, got {txt!r}"


def test_04_missing_changelog_unreleased_abort():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _setup_clean_repo(tmp)
        changelog = tmp / "CHANGELOG.md"
        t = changelog.read_text(encoding="utf-8")
        t2 = t.replace("## [Unreleased]", "## [Removed]")
        assert "## [Unreleased]" not in t2
        changelog.write_text(t2, encoding="utf-8", newline="\n")
        _git(tmp, ["add", "CHANGELOG.md"])
        _git(tmp, ["commit", "-m", "break changelog"])
        res = _run_sync(tmp, ["--check"])
        assert res.returncode == 1, f"missing CHANGELOG Unreleased should exit 1, got {res.returncode} {res.stdout} {res.stderr}"
        txt = res.stdout + res.stderr
        assert "unreleased" in txt.lower() or "changelog" in txt.lower(), f"expected changelog drift, got {txt!r}"


def test_05_semver():
    # 5a dry-run bump patch without --apply ok + no mutation
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _setup_clean_repo(tmp)
        before_hash = _sha256(tmp / "VERSION")
        before_text = (tmp / "VERSION").read_text(encoding="utf-8")
        res = _run_sync(tmp, ["--bump", "patch"])
        after_hash = _sha256(tmp / "VERSION")
        assert res.returncode == 0, f"dry-run --bump patch should exit 0, got {res.returncode} {res.stdout} {res.stderr}"
        assert "would bump" in (res.stdout + res.stderr).lower(), f"expected would bump, got {res.stdout!r} {res.stderr!r}"
        assert before_hash == after_hash, f"dry-run must not mutate VERSION: before {before_text!r} after {(tmp/'VERSION').read_text(encoding='utf-8')!r}"
    # 5b invalid kind -> exit 2
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _setup_clean_repo(tmp)
        res = _run_sync(tmp, ["--bump", "invalid"])
        assert res.returncode == 2, f"invalid kind should exit 2, got {res.returncode} {res.stdout} {res.stderr}"
    # 5c malformed VERSION -> exit 2
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _setup_clean_repo(tmp)
        (tmp / "VERSION").write_text("not-semver\n", encoding="utf-8")
        _git(tmp, ["add", "VERSION"])
        _git(tmp, ["commit", "-m", "bad version"])
        res = _run_sync(tmp, ["--bump", "patch"])
        assert res.returncode == 2, f"malformed VERSION should exit 2, got {res.returncode} {res.stdout} {res.stderr}"
        txt = (res.stdout + res.stderr).lower()
        assert "semver" in txt or "bad semver" in txt or "usage" in txt, f"expected semver error, got {txt!r}"
    # 5d semver_gt polarity direct import
    assert _RS.semver_gt("0.2.0", "0.1.0") is True, "semver_gt 0.2.0 > 0.1.0 failed"
    assert _RS.semver_gt("0.1.0", "0.2.0") is False, "semver_gt 0.1.0 > 0.2.0 should be False"
    assert _RS.semver_gt("0.1.0", "0.1.0") is False, "semver_gt equal should be False"
    # extra: bump produces greater
    assert _RS.semver_gt(_RS.semver_bump("0.1.0", "patch"), "0.1.0")
    assert _RS.semver_gt(_RS.semver_bump("0.1.0", "minor"), "0.1.0")
    assert _RS.semver_gt(_RS.semver_bump("0.1.0", "major"), "0.1.0")


def test_06_atomic_rollback():
    # 6a dirty pre-check: dirty tree -> bump --apply must not mutate VERSION
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _setup_clean_repo(tmp)
        before_hash = _sha256(tmp / "VERSION")
        before_data = (tmp / "VERSION").read_bytes()
        # make dirty
        (tmp / "README.md").write_text(
            (tmp / "README.md").read_text(encoding="utf-8") + "\ndirty\n", encoding="utf-8"
        )
        res = _run_sync(tmp, ["--bump", "patch", "--apply"])
        after_hash = _sha256(tmp / "VERSION")
        after_data = (tmp / "VERSION").read_bytes()
        assert res.returncode == 1, f"dirty bump should abort exit 1, got {res.returncode} {res.stdout} {res.stderr}"
        assert before_hash == after_hash, f"atomic rollback failed dirty pre-check: before {before_hash} after {after_hash}"
        assert before_data == after_data, "VERSION bytes mutated despite abort"
    # 6b validate failure pre-check: broken skill -> bump aborts and VERSION untouched
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _setup_clean_repo(tmp)
        # add broken skill that fails validate (invalid name)
        bad_dir = tmp / ".agents" / "skills" / "Bad_Name"
        bad_dir.mkdir(parents=True, exist_ok=True)
        bad_content = """---
name: Bad_Name
description: "Use when bad"
---
no fence
"""
        (bad_dir / "SKILL.md").write_text(bad_content, encoding="utf-8", newline="\n")
        _git(tmp, ["add", "."])
        _git(tmp, ["commit", "-m", "bad skill"])
        before_hash = _sha256(tmp / "VERSION")
        res = _run_sync(tmp, ["--bump", "patch", "--apply"])
        after_hash = _sha256(tmp / "VERSION")
        assert res.returncode == 1, f"validate-fail bump should abort exit 1, got {res.returncode} {res.stdout} {res.stderr}"
        assert before_hash == after_hash, f"atomic rollback failed validate pre-check: before {before_hash} after {after_hash}"
        txt = (res.stdout + res.stderr).lower()
        assert "validate" in txt or "drift" in txt, f"expected validate drift message, got {txt!r}"


def main():
    real_version = REPO_SRC / "VERSION"
    real_before = _sha256(real_version) if real_version.exists() else ""
    tests = [
        ("01_check_readonly_hash_proof", test_01_check_readonly_hash_proof),
        ("02_dirty_tree_abort", test_02_dirty_tree_abort),
        ("03_missing_readme_markers_abort", test_03_missing_readme_markers_abort),
        ("04_missing_changelog_unreleased_abort", test_04_missing_changelog_unreleased_abort),
        ("05_semver_dryrun_invalid_malformed_polarity", test_05_semver),
        ("06_atomic_rollback", test_06_atomic_rollback),
    ]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS: {name}")
        except AssertionError as e:
            print(f"FAIL: {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"FAIL: {name}: {e}")
            failed += 1
    # also verify semver polarity already in 05 but double-check here for required assert shape
    try:
        assert _RS.semver_gt("0.2.0", "0.1.0") and not _RS.semver_gt("0.1.0", "0.2.0") and not _RS.semver_gt("0.1.0", "0.1.0")
        print("PASS: semver_gt_polarity")
    except AssertionError as e:
        print(f"FAIL: semver_gt_polarity: {e}")
        failed += 1

    real_after = _sha256(real_version) if real_version.exists() else ""
    if real_before != real_after:
        print(f"FAIL: real_VERSION_mutated before={real_before} after={real_after}")
        failed += 1
    else:
        print(f"PASS: real_VERSION_untouched hash={real_before[:8] if real_before else 'none'}")

    if failed == 0:
        print("ALL PASS")
        return 0
    else:
        print(f"{failed} FAIL(s)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
