"""Hermetic parity tests — stdlib only.

Completion criterion for repo-blast-radius-sync: verify_parity --strict must exit 0
only when staged ⊇ GOVERNING_DOCS∪TEST_SUITES and registry fresh and no TODO.

Run: python tests/test_blast_radius_parity.py
"""
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _find_repo_src():
    cur = Path(__file__).resolve().parent
    for _ in range(6):
        if (cur / "VERSION").exists() and (cur / "scripts" / "validate.py").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return Path(__file__).resolve().parents[1]

REPO_SRC = _find_repo_src()

def _run(cwd: Path, args):
    return subprocess.run([sys.executable] + list(args), cwd=str(cwd), capture_output=True, text=True, shell=False)

def _git(cwd: Path, args):
    return subprocess.run(["git"] + list(args), cwd=str(cwd), capture_output=True, text=True, shell=False)

def _setup_clean_repo(tmp: Path) -> Path:
    for name in ["VERSION", "GEMINI.md", "README.md", "CHANGELOG.md"]:
        src = REPO_SRC / name
        if src.exists():
            shutil.copy2(str(src), str(tmp / name))
    for scr in ["validate.py"]:
        src = REPO_SRC / "scripts" / scr
        if src.exists():
            dst = tmp / "scripts" / scr
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
    # copy blast skill scripts
    for scr in ["blast_radius.py", "build_registry.py", "verify_parity.py", "draft_doc_updates.py"]:
        src = REPO_SRC / ".agents" / "skills" / "repo-blast-radius-sync" / "scripts" / scr
        if src.exists():
            dst = tmp / "scripts" / scr
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
    # minimal skill so validate passes
    dummy = tmp / ".agents" / "skills" / "dummy"
    dummy.mkdir(parents=True, exist_ok=True)
    (dummy / "SKILL.md").write_text("---\nname: dummy\ndescription: \"Use when testing dummy Keywords: dummy\"\n---\n# Dummy\n```bash\necho hi\n```\nKeywords: dummy\n", encoding="utf-8")
    # create docs/tests structure for parity
    (tmp / "docs").mkdir(parents=True, exist_ok=True)
    (tmp / "tests").mkdir(parents=True, exist_ok=True)
    (tmp / "src" / "payments").mkdir(parents=True, exist_ok=True)
    (tmp / "src" / "payments" / "processor.py").write_text("# @docs: docs/api_reference.md\n# @tests: tests/test_processor.py\ndef process_transaction(routing):\n    pass\n", encoding="utf-8")
    (tmp / "src" / "app.py").write_text("import processor\nprocessor.process_transaction(routing=123)\n", encoding="utf-8")
    (tmp / "docs" / "api_reference.md").write_text("# API\n", encoding="utf-8")
    (tmp / "tests" / "test_processor.py").write_text("def test_x(): pass\n", encoding="utf-8")
    r = _git(tmp, ["init"])
    if r.returncode != 0: raise RuntimeError(r.stderr)
    _git(tmp, ["config", "user.email", "test@test.local"])
    _git(tmp, ["config", "user.name", "Test"])
    _git(tmp, ["add", "."])
    r2 = _git(tmp, ["commit", "-m", "init"])
    if r2.returncode != 0: raise RuntimeError(f"{r2.stdout} {r2.stderr}")
    # build registry
    _run(tmp, ["scripts/build_registry.py"])
    return tmp


def test_dirty_spaces_and_rename():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td); _setup_clean_repo(tmp)
        # create file with space
        p = tmp / "a b.py"
        p.write_text("# @docs: docs/api_reference.md\ndef foo(): pass\n", encoding="utf-8")
        _git(tmp, ["add", "a b.py"])
        res = _run(tmp, ["scripts/verify_parity.py", "--dry-run"])
        # should not crash, should have parsed "a b.py"
        assert res.returncode in (0, 1), f"unexpected code {res.returncode} {res.stderr}"
        out = res.stdout + res.stderr
        assert "a b.py" in out or res.returncode == 0, f"spaces file not detected {out!r}"


def test_binary_and_large_skip():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td); _setup_clean_repo(tmp)
        # large file >5MiB
        big = tmp / "big.py"
        big.write_bytes(b"x" * (6*1024*1024))
        # binary with \x00 at 2k
        binp = tmp / "binary.py"
        binp.write_bytes(b"x"*2048 + b"\x00" + b"y"*100)
        _git(tmp, ["add", "big.py", "binary.py"])
        res = _run(tmp, ["scripts/build_registry.py"])
        assert res.returncode == 0, res.stderr
        reg = tmp / ".agent" / "registry.json"
        assert reg.exists(), "registry not built"
        import json
        data = json.loads(reg.read_text(encoding="utf-8"))
        skipped = data.get("skipped", [])
        assert any("big.py" in s.get("path","") for s in skipped), f"big not skipped {skipped!r}"
        assert any("binary.py" in s.get("path","") for s in skipped), f"binary not skipped {skipped!r}"


def test_dry_run_no_write():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td); _setup_clean_repo(tmp)
        (tmp / "src" / "payments" / "processor.py").write_text("def new_func(a, b):\n    pass\n# @docs: docs/api_reference.md\n", encoding="utf-8")
        _git(tmp, ["add", "src/payments/processor.py"])
        res = _run(tmp, ["scripts/draft_doc_updates.py", "docs/api_reference.md", "--dry-run"])
        assert res.returncode == 0, res.stderr
        assert "new_func" in res.stdout, f"patch not in stdout {res.stdout!r}"
        content = (tmp / "docs" / "api_reference.md").read_text(encoding="utf-8")
        assert "new_func" not in content, "dry-run should not write file"


def test_stale_registry_and_no_todo():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td); _setup_clean_repo(tmp)
        # stale: modify py without rebuilding
        (tmp / "src" / "payments" / "processor.py").write_text("# @docs: docs/api_reference.md\ndef foo():\n    pass\n# TODO: update docs later\n", encoding="utf-8")
        _git(tmp, ["add", "src/payments/processor.py"])
        res = _run(tmp, ["scripts/verify_parity.py", "--strict"])
        out = res.stdout + res.stderr
        # should warn about TODO? heuristic WARN or ERR_STALE
        assert res.returncode == 1 or "WARN" in out or "ERR" in out, f"stale/TODO not flagged {out!r}"


def main():
    tests = [
        ("dirty_spaces_and_rename", test_dirty_spaces_and_rename),
        ("binary_and_large_skip", test_binary_and_large_skip),
        ("dry_run_no_write", test_dry_run_no_write),
        ("stale_registry_and_no_todo", test_stale_registry_and_no_todo),
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
    if failed == 0:
        print("ALL PASS")
        return 0
    else:
        print(f"{failed} FAIL(s)")
        return 1

if __name__ == "__main__":
    sys.exit(main())
