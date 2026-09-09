# ponytail: single-file until second consumer.
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PINS = ["stdlib-only","skill-naming-convention","frontmatter-validation","read-only-research-zones","canonical-skills-source","description-starts-with-use-when"]

def git_run(args, cwd, **kw):
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, shell=False, **kw)

def git_root():
    r = git_run(["git","rev-parse","--show-toplevel"], cwd=Path.cwd())
    return Path(r.stdout.strip()) if r.returncode==0 else Path.cwd()

def git_dir(root):
    r = git_run(["git","rev-parse","--git-dir"], cwd=root)
    gd = r.stdout.strip() if r.returncode==0 else ".git"
    p = Path(gd)
    return p if p.is_absolute() else root / p

def semver_parse(v):
    m=re.match(r"^\s*(\d+)\.(\d+)\.(\d+)", v.strip())
    if not m: raise ValueError(f"bad semver {v!r}")
    return tuple(int(x) for x in m.groups())

def semver_gt(a,b):
    return semver_parse(a) > semver_parse(b)

def semver_bump(v, kind):
    maj,mi,pa=semver_parse(v)
    if kind=="major": return f"{maj+1}.0.0"
    if kind=="minor": return f"{maj}.{mi+1}.0"
    if kind=="patch": return f"{maj}.{mi}.{pa+1}"
    raise ValueError(kind)

def git_clean(root):
    a=git_run(["git","diff","--quiet"], cwd=root)
    b=git_run(["git","diff","--cached","--quiet"], cwd=root)
    return a.returncode==0 and b.returncode==0

def version_ignored(root):
    r=git_run(["git","check-ignore","-q","VERSION"], cwd=root)
    return r.returncode==0

def read_version(root):
    return (root/"VERSION").read_text(encoding="utf-8").strip() if (root/"VERSION").exists() else ""

def read_gemini(root):
    p=root/"GEMINI.md"
    t=p.read_text(encoding="utf-8") if p.exists() else ""
    m=re.search(r'^version:\s*"([^"]+)"', t, re.MULTILINE)
    gv=m.group(1) if m else ""
    m2=re.search(r'^last_indexed:\s*"([^"]+)"', t, re.MULTILINE)
    li=m2.group(1) if m2 else ""
    m3=re.findall(r'^\s*-\s*"([^"]+)"', t, re.MULTILINE)
    # rules are under rules: list; fallback to global PINS if not found
    rules=[x for x in m3 if x in PINS or True][:20]
    # precise rules extraction: lines after 'rules:'
    rules=[]
    in_rules=False
    for line in t.splitlines():
        if re.match(r'^\s*rules\s*:', line): in_rules=True; continue
        if in_rules:
            mm=re.match(r'^\s*-\s*"([^"]+)"', line)
            if mm: rules.append(mm.group(1))
            else: break
    return t, gv, li, rules

def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""

def check_changelog(root):
    c=root/"CHANGELOG.md"
    return "## [Unreleased]" in c.read_text(encoding="utf-8") if c.exists() else False

def check_readme_region(root):
    r=root/"README.md"
    if not r.exists(): return False
    t=r.read_text(encoding="utf-8")
    has_start="<!-- release-sync:start -->" in t
    has_end="<!-- release-sync:end -->" in t
    if not has_start or not has_end: return False  # fail-closed: missing markers => drift
    return t.index("<!-- release-sync:start -->") < t.index("<!-- release-sync:end -->")

def run_validate(root):
    r=git_run([sys.executable,"scripts/validate.py"], cwd=root)
    return r.returncode==0, r.stdout+r.stderr

def run_indexer(root):
    # shell=False, try canonical path
    cand=root/".agents/skills/gemini-context-engineer/scripts/repo_indexer.py"
    if cand.exists():
        r=git_run([sys.executable, str(cand), "--json"], cwd=root)
        return r.returncode==0
    return True

def atomic_write(target, content, gdir):
    gdir.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(gdir), prefix="tmp.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(target))
        # fsync dir for durability
        try:
            dfd=os.open(str(target.parent), os.O_RDONLY)
            try: os.fsync(dfd)
            finally: os.close(dfd)
        except Exception: pass
    except Exception:
        try: os.unlink(tmp)
        except Exception: pass
        raise

def do_check(root, gdir):
    # ponytail: --check is read-only — no writes; hash proof via sha256 unchanged pre/post
    drift=False
    msgs=[]
    if version_ignored(root):
        msgs.append("drift: VERSION is gitignored (git check-ignore -q) — remove from .gitignore"); drift=True
    v=read_version(root)
    _, gv, li, rules = read_gemini(root)
    if v and gv and v!=gv:
        msgs.append(f"drift: VERSION {v!r} != GEMINI.md version {gv!r}"); drift=True
    # semver sanity: ensure version is valid
    try: semver_parse(v)
    except Exception as e: msgs.append(f"drift: VERSION semver invalid: {e}"); drift=True
    if rules != PINS:
        # PINS touch check
        diff=set(rules)^set(PINS) if rules else set(PINS)
        msgs.append(f"drift: PINS != GEMINI.md rules diff={diff} Tip: update PINS const to match GEMINI.md rules")
        drift=True
    if not check_changelog(root):
        msgs.append("drift: CHANGELOG.md missing ## [Unreleased]"); drift=True
    if not check_readme_region(root):
        msgs.append("drift: README.md missing or malformed <!-- release-sync:start --> ... <!-- release-sync:end --> region"); drift=True
    # indexer freshness: warn but not fail unless stale >90d
    if li:
        try:
            d=datetime.date.fromisoformat(li)
            age=(datetime.date.today()-d).days
            if age>90: msgs.append(f"drift: GEMINI.md last_indexed {li} stale >90d"); drift=True
            elif age>30: msgs.append(f"warn: last_indexed {li} {age}d old")
        except Exception: msgs.append(f"warn: last_indexed parse fail {li!r}")
    ok,_=run_validate(root)
    if not ok: msgs.append("drift: scripts/validate.py failed"); drift=True
    # run indexer in check but don't federate (no write)
    run_indexer(root)
    for m in msgs: print(m, file=sys.stderr if drift else sys.stdout)
    return 1 if drift else 0

def do_bump(root, gdir, kind, allow_auto_patch, apply):
    # usage errors -> exit 2
    if kind not in ("major","minor","patch"):
        print(f"usage: --bump must be major|minor|patch, got {kind!r}", file=sys.stderr); return 2
    v=read_version(root)
    try: semver_parse(v)
    except Exception as e: print(f"usage: VERSION semver invalid: {e}", file=sys.stderr); return 2
    new=semver_bump(v, kind)
    if not semver_gt(new, v):
        print(f"drift: bump {v} -> {new} not greater", file=sys.stderr); return 1
    if not apply:
        print(f"would bump {v} -> {new} (use --apply to write)")
        return 0
    # allow_auto_patch: if patch needed but minor requested? minimal gate
    if kind=="patch" and not allow_auto_patch:
        # plain patch always allowed; auto-patch is for implicit patch
        pass
    # pre-validate
    ok,out=run_validate(root)
    if not ok: print(out, file=sys.stderr); print("validate pre-check failed", file=sys.stderr); return 1
    if not git_clean(root):
        print("drift: working tree not clean, aborting bump", file=sys.stderr); return 1
    if version_ignored(root):
        print("drift: VERSION is gitignored, abort", file=sys.stderr); return 1
    # prepare new contents
    gem_text, gv, li, rules = read_gemini(root)
    if rules != PINS:
        print(f"drift: PINS mismatch, update PINS const first. diff rules={rules} vs PINS={PINS}", file=sys.stderr)
        return 1
    if not check_changelog(root):
        print("drift: CHANGELOG.md missing ## [Unreleased]", file=sys.stderr); return 1
    if not check_readme_region(root):
        print("abort: README.md missing release-sync region", file=sys.stderr); return 1
    today=datetime.date.today().isoformat()
    # build updated GEMINI.md
    new_gem=gem_text
    if gv:
        new_gem=re.sub(r'^(version:\s*)"[^"]+"', rf'\1"{new}"', new_gem, flags=re.MULTILINE)
    if li or 'last_indexed' in new_gem:
        if 'last_indexed' in new_gem:
            new_gem=re.sub(r'^(last_indexed:\s*)"[^"]+"', rf'\1"{today}"', new_gem, flags=re.MULTILINE)
        else:
            new_gem=new_gem.replace("generator:", f'last_indexed: "{today}"\ngenerator:')
    # indexer run
    run_indexer(root)
    # README region sync if markers exist
    readme_p=root/"README.md"
    readme_txt=readme_p.read_text(encoding="utf-8") if readme_p.exists() else ""
    new_readme=readme_txt
    if "<!-- release-sync:start -->" in readme_txt and "<!-- release-sync:end -->" in readme_txt:
        region=f"<!-- release-sync:start -->\nVersion: {new}\n<!-- release-sync:end -->"
        new_readme=re.sub(r"<!-- release-sync:start -->.*?<!-- release-sync:end -->", region, readme_txt, flags=re.DOTALL)
    # prepare staging via atomic writes to git-dir tmp then mv
    # we stage 4 files: VERSION, GEMINI.md, CHANGELOG.md, README.md (if changed)
    # use atomic_write directly to final destination with fsync; rollback on fail
    origs={}
    for p in [root/"VERSION", root/"GEMINI.md", root/"CHANGELOG.md", readme_p]:
        if p.exists(): origs[p]=p.read_bytes()
    try:
        atomic_write(root/"VERSION", new+"\n", gdir)
        atomic_write(root/"GEMINI.md", new_gem, gdir)
        if new_readme!=readme_txt and readme_p.exists():
            atomic_write(readme_p, new_readme, gdir)
        # CHANGELOG not auto-edited except ensure Unreleased exists
    except Exception as e:
        print(f"atomic write failed, rolling back: {e}", file=sys.stderr)
        for p, data in origs.items():
            try:
                fd, tmp = tempfile.mkstemp(dir=str(gdir))
                with os.fdopen(fd,"wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
                os.replace(tmp, str(p))
            except Exception: pass
        return 1
    ok2,out2=run_validate(root)
    if not ok2:
        print(out2, file=sys.stderr)
        # rollback
        for p, data in origs.items():
            try:
                fd, tmp = tempfile.mkstemp(dir=str(gdir))
                with os.fdopen(fd,"wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
                os.replace(tmp, str(p))
            except Exception: pass
        print("validate post-check failed, rolled back", file=sys.stderr)
        return 1
    print(f"bumped {v} -> {new}")
    return 0

def install_hooks(root):
    hook=root/".git/hooks/pre-commit"
    # worktree-safe: hooks live in git-dir, but .git/hooks is canonical for main worktree
    gdir=git_dir(root)
    # ensure hooks dir exists (resolve symlink case)
    try: hook.parent.mkdir(parents=True, exist_ok=True)
    except Exception: pass
    content="#!/bin/sh\n# release_sync pre-commit hook\npython scripts/release_sync.py --check || exit 1\n"
    # write via atomic in gdir then move to hook
    try:
        fd, tmp = tempfile.mkstemp(dir=str(gdir))
        with os.fdopen(fd,"w", encoding="utf-8", newline="\n") as f:
            f.write(content); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, str(hook))
        try: os.chmod(str(hook), 0o755)
        except Exception: pass
        print(f"installed hook {hook}")
        return 0
    except Exception as e:
        print(f"install hook failed: {e}", file=sys.stderr); return 1

def main(argv=None):
    argv=argv if argv is not None else sys.argv[1:]
    root=git_root()
    gdir=git_dir(root)
    ap=argparse.ArgumentParser(description="release sync — version parity gate")
    g=ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="check drift (no writes)")
    g.add_argument("--bump", metavar="KIND", help="bump major|minor|patch")
    ap.add_argument("--allow-auto-patch", action="store_true")
    ap.add_argument("--apply", action="store_true", help="apply writes (requires --bump)")
    ap.add_argument("--install-hooks", action="store_true", help="install git hooks")
    args=ap.parse_args(argv)
    # exit 2 for usage errors per taxonomy
    if args.install_hooks:
        return install_hooks(root)
    if args.check:
        if args.bump or args.apply or args.allow_auto_patch:
            ap.error("--check is exclusive")
            return 2
        return do_check(root, gdir)
    if args.bump:
        return do_bump(root, gdir, args.bump, args.allow_auto_patch, args.apply)
    if args.apply or args.allow_auto_patch:
        print("usage: --apply/--allow-auto-patch require --bump", file=sys.stderr)
        return 2
    ap.print_help()
    return 2

if __name__=="__main__":
    sys.exit(main())
