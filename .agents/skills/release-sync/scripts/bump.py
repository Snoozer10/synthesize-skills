"""release-sync atomic version bump. Stdlib only.

Writes VERSION, GEMINI.md, package.json atomically with rollback on failure.

Exit codes: 0=success/dry-run, 1=failure, 2=usage error
Usage: bump.py major|minor|patch [--apply] [--json]
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path


SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def _find_root():
    cur = Path.cwd()
    for _ in range(6):
        if (cur / "VERSION").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return Path.cwd()


def _read_version(root):
    p = root / "VERSION"
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""


def _semver_parse(v):
    m = SEMVER_RE.match(v.strip())
    if not m:
        raise ValueError(f"bad semver: {v!r}")
    return tuple(int(x) for x in m.groups())


def _semver_bump(v, kind):
    maj, mi, pa = _semver_parse(v)
    if kind == "major":
        return f"{maj + 1}.0.0"
    if kind == "minor":
        return f"{maj}.{mi + 1}.0"
    if kind == "patch":
        return f"{maj}.{mi}.{pa + 1}"
    raise ValueError(f"unknown kind: {kind!r}")


def _atomic_write(target, content):
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), prefix="tmp.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(target))
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise


def _run_check(root):
    check_py = Path(__file__).parent / "check.py"
    r = subprocess.run(
        [sys.executable, str(check_py)],
        cwd=str(root), capture_output=True, text=True, shell=False,
    )
    return r.returncode == 0


def _git_clean(root):
    r = subprocess.run(
        ["git", "diff", "--quiet"], cwd=str(root),
        capture_output=True, text=True, shell=False,
    )
    r2 = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=str(root),
        capture_output=True, text=True, shell=False,
    )
    return r.returncode == 0 and r2.returncode == 0


def _git_ignored(root, path):
    r = subprocess.run(
        ["git", "check-ignore", "-q", path], cwd=str(root),
        capture_output=True, text=True, shell=False,
    )
    return r.returncode == 0


def bump(kind, apply=False, as_json=False, root=None):
    root = root or _find_root()

    if kind not in ("major", "minor", "patch"):
        print(f"usage: kind must be major|minor|patch, got {kind!r}", file=sys.stderr)
        return 2

    v = _read_version(root)
    try:
        _semver_parse(v)
    except ValueError as e:
        print(f"usage: {e}", file=sys.stderr)
        return 2

    new = _semver_bump(v, kind)

    if not apply:
        msg = f"would bump {v} -> {new}"
        if as_json:
            print(json.dumps({"action": "dry-run", "from": v, "to": new}))
        else:
            print(msg)
        return 0

    # pre-checks
    if not _run_check(root):
        print("error: pre-check drift detected, abort bump", file=sys.stderr)
        return 1
    if not _git_clean(root):
        print("error: working tree not clean, abort bump", file=sys.stderr)
        return 1
    if _git_ignored(root, "VERSION"):
        print("error: VERSION is gitignored, abort bump", file=sys.stderr)
        return 1

    # read originals for rollback
    originals = {}
    targets = [root / "VERSION", root / "GEMINI.md", root / "package.json"]
    for p in targets:
        if p.exists():
            originals[p] = p.read_bytes()

    today = date.today().isoformat()

    try:
        # VERSION
        _atomic_write(root / "VERSION", new + "\n")

        # GEMINI.md
        gemini = root / "GEMINI.md"
        if gemini.exists():
            t = gemini.read_text(encoding="utf-8")
            t = re.sub(r'^(version:\s*)"[^"]+"', rf'\1"{new}"', t, flags=re.MULTILINE)
            t = re.sub(r'^(last_indexed:\s*)"[^"]+"', rf'\1"{today}"', t, flags=re.MULTILINE)
            _atomic_write(gemini, t)

        # package.json
        pkg = root / "package.json"
        if pkg.exists():
            try:
                pj = json.loads(pkg.read_text(encoding="utf-8"))
                pj["version"] = new
                _atomic_write(pkg, json.dumps(pj, indent=2) + "\n")
            except Exception:
                pass

        # post-check
        if not _run_check(root):
            raise RuntimeError("post-check failed")

    except Exception as e:
        print(f"error: bump failed, rolling back: {e}", file=sys.stderr)
        for p, data in originals.items():
            try:
                _atomic_write(p, data.decode("utf-8"))
            except Exception:
                pass
        return 1

    if as_json:
        print(json.dumps({"action": "bumped", "from": v, "to": new}))
    else:
        print(f"bumped {v} -> {new}")
    return 0


def main(argv=None):
    args = list(argv or sys.argv[1:])
    as_json = "--json" in args
    apply = "--apply" in args
    args = [a for a in args if a not in ("--json", "--apply")]
    if not args:
        print("usage: bump.py major|minor|patch [--apply] [--json]", file=sys.stderr)
        return 2
    return bump(args[0], apply=apply, as_json=as_json)


if __name__ == "__main__":
    sys.exit(main())
