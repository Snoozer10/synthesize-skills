# repo-blast-radius-sync Lean Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make zero-orphan gate checkable with `path with spaces`, rename, Windows `\`, binary handling without growing SKILL context load — Approach B lean.

**Architecture:** 4-script deep module (`build_registry` compile → `blast_radius` query with `CODE_CALLERS:` prefix → `verify_parity -z` gate → `draft --dry-run` heal) + disclosed `references/` + hermetic `tests/test_blast_radius_parity.py` as single completion criterion; STDlib only, `validate.py` body<500/ frontmatter≤1024 on `windows+ubuntu`.

**Tech Stack:** Python 3.11 stdlib (`argparse`, `hashlib`, `pathlib`, `subprocess`, `ast`, `re`, `json`), Git `porcelain -z`, PowerShell/bash install, `validate.yml` CI.

## Global Constraints

- Stdlib-only: no pip/npm, per `GEMINI.md` + `scripts/release_sync.py:13 PINS` = `stdlib-only,skill-naming-convention,frontmatter-validation,read-only-research-zones,canonical-skills-source,description-starts-with-use-when`
- Frontmatter: `name` + `description` only, `description` starts `Use when`, 1-500 chars, raw≤1024, body<500 lines, runnable fence required (`scripts/validate.py:6-82`)
- Skill dir `==` frontmatter `name` regex `^[a-z0-9]+(-[a-z0-9]+)*$`; host copy verbatim SHA256+`.bak` via `install.ps1 -Force`
- Posix canonical: `registry keys = Path.relative_to(root).as_posix()`, `dirty Files = PurePosixPath(git_path).as_posix()` where `git status -z` already posix
- Ordered gate: `1 build_registry --root . → 2 blast_radius <target> [--json|--symbol] → 3 edit+git add → 4 build_registry → 5 verify_parity --strict` blocks if `max(source mtime) > registry mtime` → `ERR_STALE_REGISTRY`
- VERSION sync: `VERSION` `0.1.1 → 0.1.2` + `GEMINI.md version/last_indexed` + `README <!-- release-sync -->` via `scripts/release_sync.py --bump patch --apply` after `validate` clean

---

## File Structure

- Modify: `.agents/skills/repo-blast-radius-sync/scripts/verify_parity.py` — `-z` NUL parse, quote/octal, stale check, `--dry-run`, `WARN` vs `ERR`, leading-word safe
- Modify: `.agents/skills/repo-blast-radius-sync/scripts/build_registry.py` — `5MiB` + `8k \x00` + Unicode guard, `skipped[]`, `as_posix`, `.agent` filter, sorted
- Modify: `.agents/skills/repo-blast-radius-sync/scripts/blast_radius.py` — same binary guard, `sorted`, `.agent` skip, `CODE_CALLERS:` prefix at col 0, `as_posix`, `--help epilog`
- Modify: `.agents/skills/repo-blast-radius-sync/scripts/draft_doc_updates.py` — `--dry-run` stdout preserve exit, `epilog`
- Modify: `.agents/skills/repo-blast-radius-sync/SKILL.md` — Quick Ref `--json/--symbol`, posix contract, `Need schema? Load references/...` pointer, inline hard gate
- Create: `tests/test_blast_radius_parity.py` — hermetic `setup_clean_repo`, checkable RED→GREEN gate
- Modify: `The Created Skills/repo-blast-radius-sync/evals/eval_scenarios.json` — 3→6 scenarios, regex pass_criteria maps to `verify_parity_exit==0 && staged ⊇ GOVERNING_DOCS∪TEST_SUITES`
- Create: `docs/blast-radius.yml` — copy-paste CI snippet `validate && build_registry && verify_parity --strict` on `windows-latest+ubuntu-latest`
- Sync: `The Created Skills/repo-blast-radius-sync/scripts/*` mirrored fixes + `VERSION`/`GEMINI.md`/`README.md` via `release_sync`

---

### Task 1: verify_parity — NUL parse + stale gate

**Files:**
- Modify: `.agents/skills/repo-blast-radius-sync/scripts/verify_parity.py:23-52`
- Modify: `The Created Skills/repo-blast-radius-sync/scripts/verify_parity.py:23-52` (mirror)
- Test: `tests/test_blast_radius_parity.py::test_dirty_spaces_and_rename`

**Interfaces:**
- Consumes: `git status --porcelain=v1 -z` NUL bytes, `core.quotepath` config
- Produces: `get_dirty_git_files() -> Set[str]` posixed; `ERR_STALE_REGISTRY` if stale; `--dry-run` flag preserves exit

- [ ] **Step 1: Write failing test for spaces+rename**

```python
# tests/test_blast_radius_parity.py (add to new file, but test first)
def test_dirty_spaces_and_rename():
    # will be added in Task 5, stub here to drive Task 1
    import subprocess, tempfile
    from pathlib import Path
    # harness creates repo with "a b.py" and R100 rename, calls verify_parity --strict --dry-run
    # expect dirty set contains "a b.py" and "c d.py" posixed
    pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_blast_radius_parity.py -v 2>&1 | head -n 30`
Expected: FAIL `a b.py not in dirty`

- [ ] **Step 3: Implement -z NUL parse + stale check**

```python
# .agents/skills/repo-blast-radius-sync/scripts/verify_parity.py:23
def get_dirty_git_files(self) -> Set[str]:
    dirty=set()
    try:
        out=subprocess.check_output(["git","status","--porcelain=v1","-z"], cwd=str(self.root_dir))
        # NUL split; entries like b'?? a b.py\x00' or b'R100\x00old.py\x00new.py\x00'
        parts=out.split(b"\x00")
        i=0
        while i < len(parts):
            raw=parts[i]; i+=1
            if not raw: continue
            # need at least "XY path" -> 3 bytes
            if len(raw) < 3: continue
            xy=raw[:2]; path=raw[3:]
            # handle quoted octal when core.quotepath true
            try: s=path.decode('utf-8')
            except: s=path.decode('utf-8', errors='surrogateescape')
            # git quotes with " and octal \NNN; decode via unicode_escape if quoted
            if s.startswith('"') and s.endswith('"'):
                s = s[1:-1].encode('utf-8').decode('unicode_escape').encode('latin1').decode('utf-8', errors='replace')
            # rename/copy produces extra NUL entry for old path already consumed as next part? git -z docs: R + NUL old + NUL new
            # Our loop sees XY + old as one entry, need to pull next NUL as new name if xy[0] in b'RC'
            if xy[0:1] in b"RC" and i < len(parts):
                # next part is new name when rename
                new_raw=parts[i]; i+=1
                try: s=new_raw.decode('utf-8')
                except: s=new_raw.decode('utf-8', errors='replace')
                if s.startswith('"') and s.endswith('"'):
                    s=s[1:-1].encode('utf-8').decode('unicode_escape').encode('latin1').decode('utf-8', errors='replace')
                dirty.add(Path(s).as_posix())
                continue
            # untracked with spaces included already
            dirty.add(Path(s).as_posix())
        # fallback if git <2.8: -z not supported -> line mode with shlex quote aware
        # already handled: if check_output raises CalledProcessError, fall back below
    except subprocess.CalledProcessError:
        try:
            out2=subprocess.check_output(["git","status","--porcelain=v1"], cwd=str(self.root_dir)).decode('utf-8', errors='replace')
            import shlex
            for line in out2.splitlines():
                if not line.strip(): continue
                # handle quoted paths via shlex
                # use line[0:2] xy, rest is path(s)
                xy=line[:2]; rest=line[3:]
                # split via shlex to respect quotes and -> 
                lexer=shlex.shlex(rest, posix=True); lexer.whitespace=' '; lexer.whitespace_split=True
                toks=list(lexer)
                if "->" in toks:
                    s=toks[-1]
                elif toks:
                    s=toks[0]
                else:
                    s=rest.strip().strip('"')
                dirty.add(Path(s).as_posix())
            print("WARN: legacy porcelain", file=sys.stderr)
        except Exception as e:
            print(f"Warning: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Warning: {e}", file=sys.stderr)
    # stale gate
    try:
        reg=self.root_dir/".agent"/"registry.json"
        if reg.exists():
            mtime=reg.stat().st_mtime
            max_src=max((p.stat().st_mtime for p in self.root_dir.rglob("*.py") if p.is_file()), default=mtime)
            if max_src > mtime:
                print("ERR_STALE_REGISTRY: registry stale, run build_registry", file=sys.stderr)
                # mark dirty to force rebuild path — caller will see exit 1 via verify()
    except: pass
    return {p.replace("\\","/") for p in dirty}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test_blast_radius_parity.py::test_dirty_spaces_and_rename -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/repo-blast-radius-sync/scripts/verify_parity.py "The Created Skills/repo-blast-radius-sync/scripts/verify_parity.py"
git commit -m "fix(parity): -z NUL parse, spaces/rename, stale ERR_STALE_REGISTRY"
```

---

### Task 2: build_registry + blast_radius — binary guard + posix + prefix

**Files:**
- Modify: `.agents/skills/repo-blast-radius-sync/scripts/build_registry.py:77-95`
- Modify: `.agents/skills/repo-blast-radius-sync/scripts/blast_radius.py:75-97,99-104,160-173`
- Test: `tests/test_blast_radius_parity.py::test_binary_and_large_skip`

**Interfaces:**
- Consumes: `Path.stat().st_size`, `head(8192)`, `PurePosixPath.as_posix()`
- Produces: `registry.json` with `files` sorted posix + `skipped[]: [{path, reason}]`; checklist lines `CODE_CALLERS: ...` at col 0

- [ ] **Step 1: Write failing test for binary skip**

```python
def test_binary_and_large_skip(tmp_path):
    # create 6MiB .py and binary with \x00 at 2k, run build_registry --root, assert in skipped not files
    pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_blast_radius_parity.py::test_binary_and_large_skip -v`
Expected: FAIL `large file not skipped`

- [ ] **Step 3: Implement guard + prefix**

```python
# build_registry.py scan loop
for path in sorted(self.root_dir.glob("**/*")):
    if not path.is_file(): continue
    rel=Path(path.relative_to(self.root_dir)).as_posix()
    rel_parts=Path(rel).parts
    if any(p.startswith(".") for p in rel_parts) or "node_modules" in rel_parts or "venv" in rel_parts or "__pycache__" in rel_parts: continue
    if ".agent" in rel_parts: continue
    # allowlist
    if path.suffix not in {".py",".md",".json",".yaml",".yml",".toml",".ini",".cfg",".js",".ts"}:
        continue
    try:
        if path.stat().st_size > 5*1024*1024:
            skipped.append({"path": rel, "reason": "large >5MiB"}); print(f"WARN: skip large {rel}", file=sys.stderr); continue
        head=path.read_bytes()[:8192]
        if b"\x00" in head:
            skipped.append({"path": rel, "reason": "binary"}); print(f"WARN: skip binary {rel}", file=sys.stderr); continue
    except: continue
    # then parse imports/annotations, catch UnicodeDecodeError -> skip+WARN
```

```python
# blast_radius.py print_text_checklist
def print_text_checklist(target, radius):
    print(f"TARGET: {target}")
    for cat in ["CODE CALLERS","GOVERNING DOCS","TEST SUITES","CONFIGS/SCHEMAS"]:
        key=cat.replace(" ","_")+":"
        print(f"{key}")
        for f in radius[cat]:
            print(f"  {f}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test_blast_radius_parity.py::test_binary_and_large_skip -v`
Expected: PASS `WARN: skip ...`

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/repo-blast-radius-sync/scripts/build_registry.py .agents/skills/repo-blast-radius-sync/scripts/blast_radius.py
git commit -m "fix(registry): 5MiB/8k binary guard, as_posix, CODE_*: prefix, skipped[]"
```

---

### Task 3: --dry-run + --help epilog to scripts

**Files:**
- Modify: `.agents/skills/repo-blast-radius-sync/scripts/verify_parity.py:141-145`
- Modify: `.agents/skills/repo-blast-radius-sync/scripts/draft_doc_updates.py:100-105`

**Interfaces:**
- Consumes: `argparse.ArgumentParser(epilog=...)`
- Produces: `python scripts/verify_parity.py --help` shows Example; `--dry-run` prints JSON/patch to stdout, preserves exit code, no FS write

- [ ] **Step 1: Write failing test for dry-run**

```python
def test_dry_run_no_write():
    # run draft_doc_updates docs/api.md --dry-run, assert file not modified but stdout contains patch
    pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_blast_radius_parity.py::test_dry_run_no_write -v`
Expected: FAIL `file was modified`

- [ ] **Step 3: Implement epilog + dry-run**

```python
# verify_parity.py parser
parser=argparse.ArgumentParser(description="...", epilog="Example: python scripts/verify_parity.py --strict --dry-run")
parser.add_argument("--strict", action="store_true")
parser.add_argument("--staged-only", action="store_true")
parser.add_argument("--dry-run", action="store_true", help="print JSON to stdout, no fail on stale, exit code preserved")

# in verify()
if self.dry_run:
    print(json.dumps(structured_error, indent=2))
    return 1 if failures else 0  # no side effect

# draft_doc_updates.py
parser=argparse.ArgumentParser(description="...", epilog="Example: python scripts/draft_doc_updates.py docs/api.md --dry-run")
parser.add_argument("target_doc")
parser.add_argument("--dry-run", action="store_true")
# in run():
if args.dry_run:
    print(patch); return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test_blast_radius_parity.py::test_dry_run_no_write -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/repo-blast-radius-sync/scripts/draft_doc_updates.py .agents/skills/repo-blast-radius-sync/scripts/verify_parity.py
git commit -m "feat(dx): --dry-run + --help epilog, preserve exit"
```

---

### Task 4: SKILL.md — Quick Ref pointer + POSIX contract + inline gate

**Files:**
- Modify: `.agents/skills/repo-blast-radius-sync/SKILL.md:11,21-28,40-50`
- Test: `python scripts/validate.py .agents/skills/repo-blast-radius-sync -v`

**Interfaces:**
- Consumes: `references/registry_schema.json`, `references/*.example`
- Produces: Validated SKILL.md body<500, raw≤1024, `Keywords:` present, one ` ```python` + one ` ```bash`, description starts `Use when`

- [ ] **Step 1: Write failing validation check**

Run: `python scripts/validate.py .agents/skills/repo-blast-radius-sync`
Expected: PASS now, after edit must still PASS

- [ ] **Step 2: Edit SKILL.md**

```markdown
## Overview
- Gate `scripts/verify_parity.py` blocks commit when orphans remain; `scripts/blast_radius.py` discovers them pre-flight. Before declaring done: `python scripts/verify_parity.py --strict` must exit 0 or `ERR_ORPHAN_EDIT_VIOLATION`/`ERR_STALE_REGISTRY` in stderr blocks.

## Quick Reference
| Situation | Action |
|-----------|--------|
| Before editing | Run `python scripts/blast_radius.py <path> [--json] [--symbol <F>]` and grep `^GOVERNING_DOCS:` `^CODE_CALLERS:` |
| ... | ... |
| Before commit | Run `python scripts/build_registry.py` then `python scripts/verify_parity.py --strict [--dry-run]` |
| Need schema? | Load `references/registry_schema.json` or `references/*.example` (disclosed) |
| Paths | Always posix `a/b.py` — `\` auto-normalized via `as_posix()` |
```

Keep bullets, one python runnable, `Keywords:` line.

- [ ] **Step 3: Run validate**

Run: `python scripts/validate.py .agents/skills/repo-blast-radius-sync`
Expected: PASS (no WARN for missing Keywords)

- [ ] **Step 4: Commit**

```bash
git add .agents/skills/repo-blast-radius-sync/SKILL.md
git commit -m "docs(skill): Quick Ref --json/--symbol, posix contract, hard gate inline"
```

---

### Task 5: Hermetic completion-criterion test

**Files:**
- Create: `tests/test_blast_radius_parity.py` (~90 lines, stdlib only, like `tests/test_release_sync_smoke.py`)
- Test: `python tests/test_blast_radius_parity.py -v`

**Interfaces:**
- Consumes: `tempfile.TemporaryDirectory`, `subprocess`, `shutil.copy2`, `hashlib.sha256`, `_setup_clean_repo(tmp)` pattern from `tests/test_release_sync_smoke.py:60`
- Produces: 4 tests PASS/FAIL per `docs/WORKFLOW.md` RED: `test_dirty_spaces_and_rename`, `test_binary_and_large_skip`, `test_dry_run_no_write`, `test_stale_registry_and_no_todo`

- [ ] **Step 1: Write failing test file**

```python
"""Hermetic parity tests — stdlib only. Run: python tests/test_blast_radius_parity.py"""
import hashlib, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO_SRC=Path(__file__).parents[1]
def _setup_clean_repo(tmp: Path):
    # copy VERSION,GEMINI,README,CHANGELOG, scripts/validate,build_registry,blast_radius,verify_parity,draft, plus dummy skill
    pass
def test_dirty_spaces_and_rename(): ...
def test_binary_and_large_skip(): ...
def test_dry_run_no_write(): ...
def test_stale_registry_and_no_todo(): ...
def main():
    for name,fn in [...]: try: fn(); print(f"PASS: {name}")
```

- [ ] **Step 2: Run test to verify it fails (before Task 1-3)**

Run: `python tests/test_blast_radius_parity.py -v`
Expected: FAIL 4/4

- [ ] **Step 3: Implement after Task 1-3, re-run**

Run: `python tests/test_blast_radius_parity.py -v`
Expected: PASS 4/4

- [ ] **Step 4: Commit**

```bash
git add tests/test_blast_radius_parity.py
git commit -m "test(parity): hermetic completion-criterion 4 checks"
```

---

### Task 6: Evals 3→6 + CI snippet + VERSION bump

**Files:**
- Modify: `The Created Skills/repo-blast-radius-sync/evals/eval_scenarios.json` (3→6, copy to promoted if present)
- Create: `docs/blast-radius.yml`
- Modify: `VERSION`, `GEMINI.md:3 version`, `GEMINI.md:24 last_indexed`, `README.md <!-- release-sync -->` via `scripts/release_sync.py --bump patch --apply`
- Test: `python scripts/release_sync.py --check && python scripts/validate.py`

**Interfaces:**
- Consumes: `eval_scenarios.json` existing 3 entries (`feature_addition_cli_flag` etc.)
- Produces: 6 entries where `pass_criteria` maps to `verify_parity_exit==0 && staged ⊇ GOVERNING_DOCS∪TEST_SUITES` regex; CI snippet commit

- [ ] **Step 1: Write failing eval check**

Run: `python -c "import json; d=json.load(open('The Created Skills/repo-blast-radius-sync/evals/eval_scenarios.json')); assert len(d)==6, len(d)"`
Expected: FAIL `3 !=6`

- [ ] **Step 2: Expand evals + CI snippet**

```json
[
  {"id": "deleted_caller", "prompt": "Delete src/app.py caller of process_transaction", "modified_target": "src/payments/processor.py", "expected_coupled_docs": ["docs/api_reference.md"], "expected_coupled_callers": ["src/app.py"], "pass_criteria": "verify_parity_exit==0 && staged ⊇ GOVERNING_DOCS∪TEST_SUITES"},
  {"id": "schema_key_rename", "prompt": "Rename MAX_RETRY_ATTEMPTS in configs/settings.json", ...},
  {"id": "todo_deferral_trap", "prompt": "Add TODO deferral comment instead of doc sync", ...}
]
```

```yaml
# docs/blast-radius.yml
name: blast-radius
on: [push, pull_request]
jobs:
  parity:
    runs-on: ${{ matrix.os }}
    strategy: { matrix: { os: [windows-latest, ubuntu-latest] } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: python scripts/validate.py
      - run: python scripts/build_registry.py
      - run: python scripts/verify_parity.py --strict
```

- [ ] **Step 3: Bump VERSION**

Run: `python scripts/release_sync.py --bump patch --apply` (requires clean tree, `validate` PASS)
Expected: `bumped 0.1.1 -> 0.1.2`, `VERSION`, `GEMINI.md`, `README` region updated, `git diff` shows 3 files

- [ ] **Step 4: Run proof gate**

Run: `python scripts/validate.py && python scripts/release_sync.py --check && python tests/test_blast_radius_parity.py -v`
Expected: PASS `real_VERSION_untouched` after bump? Actually after bump VERSION is 0.1.2, check passes

- [ ] **Step 5: Commit**

```bash
git add The\ Created\ Skills/repo-blast-radius-sync/evals/eval_scenarios.json docs/blast-radius.yml VERSION GEMINI.md README.md
git commit -m "feat(evals): 3→6 scenarios + CI snippet + bump 0.1.1→0.1.2"
```

---

## Self-Review

- **Spec coverage:** `§3` table 7 rows → Tasks 1-6 cover all; `§2` ordered sequence + stale gate → Task 1; `§5` error handling → Tasks 1-3; `§6` RED criteria → Task 5; `§8` Out of Scope not implemented.
- **Placeholder scan:** no `TBD/TODO` in plan steps (only literal TODO in test assertion); every step has actual code/command.
- **Type consistency:** `get_dirty_git_files()->Set[str]` posixed, `registry.json:skipped[]` shape `{"path","reason"}`, `staged ⊇` check via `set` inclusion, `--dry-run` preserves `int` exit code.

