"""release-sync drift gate. Stdlib only.

80/20 rule: FAIL (exit 1) only on version parity mismatch.
All other hygiene checks are WARN (exit 0, stderr warn:).

Exit codes: 0=clean, 1=version drift, 2=usage error
Usage: check.py [--json]
"""
import json
import re
import subprocess
import sys
from pathlib import Path


SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


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


def _read_gemini_version(root):
    p = root / "GEMINI.md"
    if not p.exists():
        return ""
    t = p.read_text(encoding="utf-8")
    m = re.search(r'^version:\s*"([^"]+)"', t, re.MULTILINE)
    return m.group(1) if m else ""


def _read_package_version(root):
    p = root / "package.json"
    if not p.exists():
        return ""
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("version", "")
    except Exception:
        return ""


def _run_validate(root):
    r = subprocess.run(
        [sys.executable, str(root / "scripts" / "validate.py")],
        cwd=str(root), capture_output=True, text=True, shell=False,
    )
    return r.returncode == 0


def check(root=None, as_json=False):
    root = root or _find_root()
    drift = False
    details = {}
    errors = []
    warnings = []

    v = _read_version(root)
    gv = _read_gemini_version(root)
    pv = _read_package_version(root)

    # semver validity
    if v and not SEMVER_RE.match(v):
        errors.append(f"VERSION semver invalid: {v!r}")
        drift = True

    # version parity — the only FAIL condition
    if v and gv and v != gv:
        errors.append(f"version drift: VERSION={v} GEMINI.md={gv}")
        drift = True
    if v and pv and v != pv:
        errors.append(f"version drift: VERSION={v} package.json={pv}")
        drift = True

    # validate.py gate
    if not _run_validate(root):
        errors.append("validate.py failed")
        drift = True

    # WARN-level checks (never FAIL)
    p = root / "GEMINI.md"
    if p.exists():
        t = p.read_text(encoding="utf-8")
        # last_indexed freshness
        m = re.search(r'^last_indexed:\s*"([^"]+)"', t, re.MULTILINE)
        if m:
            from datetime import date
            try:
                d = date.fromisoformat(m.group(1))
                age = (date.today() - d).days
                if age > 90:
                    warnings.append(f"last_indexed {m.group(1)} stale >90d")
                elif age > 30:
                    warnings.append(f"last_indexed {m.group(1)} {age}d old")
            except Exception:
                pass

    # README region (warn only)
    readme = root / "README.md"
    if readme.exists():
        rt = readme.read_text(encoding="utf-8")
        if "<!-- release-sync:start -->" not in rt or "<!-- release-sync:end -->" not in rt:
            warnings.append("README.md missing release-sync region")

    # CHANGELOG (warn only)
    cl = root / "CHANGELOG.md"
    if cl.exists() and "## [Unreleased]" not in cl.read_text(encoding="utf-8"):
        warnings.append("CHANGELOG.md missing ## [Unreleased]")

    for w in warnings:
        print(f"warn: {w}", file=sys.stderr)

    for e in errors:
        print(f"error: {e}", file=sys.stderr)

    if as_json:
        out = {
            "status": "drift" if drift else "clean",
            "version": v,
            "gemini_version": gv,
            "package_version": pv,
            "errors": errors,
            "warnings": warnings,
        }
        print(json.dumps(out, indent=2))
    else:
        if not drift and not warnings:
            print("clean")

    return 1 if drift else 0


def main(argv=None):
    args = list(argv or sys.argv[1:])
    as_json = "--json" in args
    return check(as_json=as_json)


if __name__ == "__main__":
    sys.exit(main())
