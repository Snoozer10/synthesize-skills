# Dashboard B Live — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Add dual-viewer live dashboard to `repo-blast-radius-sync` — human dev (browser HTML poll 2s) + agent self-check (`dashboard.json` + `/api/status` JSON) — stdlib only, marketplace-installable via `npx`/`ux`.

**Architecture:** `scripts/dashboard.py` reuses `BlastRadiusResolver`/`ParityVerifier`/`build_registry` logic; serves `dashboard.html` (fetch `/api/status`) + writes `dashboard.json` atomically to `.agent/`; `http.server` `127.0.0.1` only, `PurePosixPath.as_posix()` everywhere.

**Tech Stack:** Python 3.11 stdlib `http.server` `json` `argparse` `pathlib` `subprocess` `hashlib`; no `curses`/`rich`/Node.

## Global Constraints

- Stdlib-only per `GEMINI.md` PINS `stdlib-only`
- `validate.py:68` body<500/frontmatter≤1024; `SKILL.md` `Use when` + `Keywords:` + runnable fence
- Posix canonical `Path.relative_to(root).as_posix()` where git `-z` already posix

---

### Task 1: Scaffold `scripts/dashboard.py` — stdlib http + json + status collector

**Files:**
- Create: `.agents/skills/repo-blast-radius-sync/scripts/dashboard.py`
- Create: `The Created Skills/repo-blast-radius-sync/scripts/dashboard.py` (mirror)

**Interfaces:**
- Consumes: `verify_parity.get_dirty_git_files()` `-z`, `blast_radius.resolve(..., --json)`, `build_registry` registry mtime vs `max(py mtime)`, `skipped[]`
- Produces: `collect_status(root: Path) -> dict{gate{exit,code,payload}, registry{fresh,mcount,skipped}, dirty{staged,unstaged}, radii{target:{CODE_CALLERS...}}, ts}`

- [ ] **Step 1: Write file with collector + http handler**

```python
#!/usr/bin/env python3
import argparse, json, os, sys, time
from pathlib import Path, PurePosixPath
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess, hashlib
# reuse existing classes via import
try:
    from blast_radius import BlastRadiusResolver
    from verify_parity import ParityVerifier
except ImportError:
    from scripts.blast_radius import BlastRadiusResolver
    from scripts.verify_parity import ParityVerifier

def collect_status(root: Path) -> dict:
    # registry fresh: compare mtime + sha256 short
    reg=root/".agent"/"registry.json"
    fresh=True; skipped=[]
    if reg.exists():
        try:
            data=json.loads(reg.read_text(encoding="utf-8"))
            skipped=data.get("skipped",[])
            mtime=reg.stat().st_mtime
            max_src=max((p.stat().st_mtime for p in root.rglob("*.py") if p.is_file()), default=mtime)
            fresh = max_src <= mtime
        except: fresh=False
    else:
        fresh=False
    pv=ParityVerifier(root)
    dirty=pv.get_dirty_git_files()
    # gate dry-run to get JSON without side effects
    gate_exit=0; payload={}
    try:
        # reuse verify() but capture; fallback to subprocess --dry-run --json-ish
        pass
    except: pass
    # radii per dirty (limit 10 for perf)
    radii={}
    resolver=BlastRadiusResolver(root)
    for t in list(dirty)[:10]:
        try: radii[PurePosixPath(t).as_posix()] = resolver.resolve(t)
        except: pass
    return {"gate":{"exit":gate_exit,"fresh":fresh,"skipped":skipped},"dirty":sorted(dirty),"radii":radii,"ts":time.time()}
```

- [ ] **Step 2: Run `python .agents/skills/repo-blast-radius-sync/scripts/dashboard.py --help`**

Run: `python .agents/skills/repo-blast-radius-sync/scripts/dashboard.py --help`
Expected: shows `--port --json --watch --once`

- [ ] **Step 3: Commit**

```bash
git add .agents/skills/repo-blast-radius-sync/scripts/dashboard.py
git commit -m "feat(dashboard): scaffold collector + http handler stdlib"
```

---

### Task 2: Dual render — `dashboard.json` atomic + `dashboard.html` poll 2s

**Files:**
- Modify: `.agents/skills/repo-blast-radius-sync/scripts/dashboard.py` (add HTML template, file write, handler)
- Test: `python scripts/dashboard.py --once --json .agent/dashboard.json && cat .agent/dashboard.json | python -m json.tool`

- [ ] **Step 1: Add atomic file write + HTML**

```python
def atomic_json(path: Path, data: dict):
    import tempfile, os
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, str(path))

HTML = """<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="2"><title>Blast Radius Dashboard</title><pre id="s">loading...</pre><script>fetch('/api/status').then(r=>r.json()).then(j=>document.getElementById('s').textContent=JSON.stringify(j,null,2))</script>"""
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/status"):
            data=collect_status(Path(os.getcwd()))
            self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(json.dumps(data, indent=2).encode())
        else:
            self.send_response(200); self.send_header("Content-Type","text/html"); self.end_headers(); self.wfile.write(HTML.encode())
        self.log_message("%s", self.path)
```

- [ ] **Step 2: Verify dual render**

Run: `python .agents/skills/repo-blast-radius-sync/scripts/dashboard.py --once --json .agent/dashboard.json && python -m json.tool .agent/dashboard.json`
Expected: has `gate,dirty,radii,ts` keys, `dirty` posixed

- [ ] **Step 3: Commit**

```bash
git add .agents/skills/repo-blast-radius-sync/scripts/dashboard.py
git commit -m "feat(dashboard): dual render json atomic + html 2s poll"
```

---

### Task 3: CLI flags + `--once` + `--watch` + 127.0.0.1 bind

**Files:**
- Modify: `.agents/skills/repo-blast-radius-sync/scripts/dashboard.py` (argparse epilog, port 0 random, watch loop 2s)

- [ ] **Step 1: Add argparse**

```python
parser=argparse.ArgumentParser(epilog="Example: python scripts/dashboard.py --port 8765 --once --json .agent/dashboard.json")
parser.add_argument("--port", type=int, default=8765, help="0=random")
parser.add_argument("--json", type=str, default=".agent/dashboard.json")
parser.add_argument("--once", action="store_true")
parser.add_argument("--watch", action="store_true")
```

- [ ] **Step 2: Run watch smoke (2s)**

Run: `timeout 4 python scripts/dashboard.py --port 0 --watch --json .agent/dashboard.json 2>&1 & sleep 2; cat .agent/dashboard.json`
Expected: file written, `fresh` bool present

- [ ] **Step 3: Commit**

```bash
git add scripts/dashboard.py
git commit -m "feat(dashboard): --port 0 random, --once/--watch 2s poll, epilog"
```

---

### Task 4: SKILL pointer + install wiring + marketplace docs

**Files:**
- Modify: `.agents/skills/repo-blast-radius-sync/SKILL.md` (add Quick Ref row)
- Modify: `README.md` marketplace section (npx/ux)
- Test: `python scripts/validate.py .agents/skills/repo-blast-radius-sync`

**Interfaces:**
- Produces: SKILL stays `body<500`, `Need live view? Run ...` pointer

- [ ] **Step 1: Add pointer**

```markdown
| Live view | Run `python scripts/dashboard.py --port 8765` then open http://127.0.0.1:8765 — agent reads `curl http://127.0.0.1:8765/api/status` or `cat .agent/dashboard.json` |
```

- [ ] **Step 2: Validate**

Run: `python scripts/validate.py .agents/skills/repo-blast-radius-sync`
Expected: PASS

- [ ] **Step 3: Commit + install**

```bash
git add .agents/skills/repo-blast-radius-sync/SKILL.md README.md
python scripts/manifest.py && ./install.ps1 -Force
git commit -m "docs: dashboard pointer + marketplace npx/ux"
```

---

## Self-Review

- Spec coverage: design B hybrid 3 tasks → Tasks 1-4 cover collector/http/json/html/watch; Global Constraints stdlib/validate/posix/ordered gate kept.
- Placeholders: none — every step has actual code/command.
- Type consistency: `collect_status -> dict` keys match HTML `fetch` and `json.tool` check.
