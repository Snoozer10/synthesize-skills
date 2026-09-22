#!/usr/bin/env python3
"""Live dashboard for repo-blast-radius-sync — human HTML + agent JSON, stdlib only."""
import argparse
import json
import os
import sys
import time
import tempfile
from pathlib import Path, PurePosixPath
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess

try:
    from blast_radius import BlastRadiusResolver
    from verify_parity import ParityVerifier
except ImportError:
    from scripts.blast_radius import BlastRadiusResolver
    from scripts.verify_parity import ParityVerifier

HTML = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Blast Radius Dashboard</title><style>body{font-family:ui-monospace,monospace;padding:16px} pre{white-space:pre-wrap;background:#f6f6f6;padding:12px;border-radius:8px} a{color:#0366d6}</style><h1>Blast Radius — Live</h1><p>Human: this page polls <code>/api/status</code> every 2s. Agent: <code>curl http://127.0.0.1:PORT/api/status</code> or <code>cat .agent/dashboard.json</code></p><pre id="s">loading...</pre><script>async function tick(){try{const r=await fetch('/api/status');const j=await r.json();document.getElementById('s').textContent=JSON.stringify(j,null,2)}catch(e){document.getElementById('s').textContent=e}};tick();setInterval(tick,2000)</script>"""

def collect_status(root: Path) -> dict:
    root = root.resolve()
    reg = root / ".agent" / "registry.json"
    fresh = False
    skipped = []
    reg_mtime = 0
    try:
        if reg.exists():
            reg_mtime = reg.stat().st_mtime
            data = json.loads(reg.read_text(encoding="utf-8"))
            skipped = data.get("skipped", [])
            max_src = max((p.stat().st_mtime for p in root.rglob("*.py") if p.is_file()), default=reg_mtime)
            fresh = max_src <= reg_mtime
    except Exception:
        fresh = False
    # gate
    gate_exit = 0
    gate_code = "PASS"
    payload = {}
    dirty = []
    try:
        pv = ParityVerifier(root)
        dirty = sorted(pv.get_dirty_git_files())
        # reuse verify logic lightly: run verifier to get failures without side effect
        # call verify() but capture; if dry_run available, use it
        # fallback: subprocess --dry-run if available
        gate_exit = pv.verify() if hasattr(pv, "verify") else 0
        # determine code from stderr is not easily captured here, infer from dirty vs radii
        if gate_exit != 0:
            gate_code = "ERR_ORPHAN_EDIT_VIOLATION"
        elif not fresh and reg.exists():
            gate_code = "ERR_STALE_REGISTRY" if dirty else "WARN_STALE"
    except Exception as e:
        gate_exit = 2
        gate_code = f"ERR: {e}"
    # radii per dirty (cap 12 for perf)
    radii = {}
    try:
        resolver = BlastRadiusResolver(root)
        for t in dirty[:12]:
            try:
                radii[PurePosixPath(t).as_posix()] = resolver.resolve(t)
            except Exception:
                continue
    except Exception:
        pass
    return {
        "gate": {"exit": gate_exit, "code": gate_code, "fresh": fresh, "skipped": skipped, "mtime": reg_mtime},
        "dirty": dirty,
        "radii": radii,
        "ts": time.time(),
        "hint": "human: open http://127.0.0.1:PORT — agent: curl /api/status or cat .agent/dashboard.json"
    }

def atomic_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(path))
    except Exception:
        try: os.unlink(tmp)
        except: pass
        raise

class Handler(BaseHTTPRequestHandler):
    root = Path.cwd()

    def do_GET(self):
        if self.path.startswith("/api/status"):
            data = collect_status(self.root)
            body = json.dumps(data, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.client_address[0]} - - [{self.log_date_time_string()}] {fmt%args}\n")

def main(argv=None):
    ap = argparse.ArgumentParser(description="Live dashboard for repo-blast-radius-sync", epilog="Example: python scripts/dashboard.py --port 8765 --once --json .agent/dashboard.json")
    ap.add_argument("--port", type=int, default=8765, help="0=random")
    ap.add_argument("--json", dest="json_path", type=str, default=".agent/dashboard.json", help="path for dashboard.json")
    ap.add_argument("--once", action="store_true", help="collect once and exit (writes json)")
    ap.add_argument("--watch", action="store_true", help="poll 2s, rewrite json")
    ap.add_argument("--root", type=str, default=".", help="repo root")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    Handler.root = root
    if args.once or args.watch:
        jp = Path(args.json_path)
        if not jp.is_absolute():
            jp = root / jp
        if args.once:
            atomic_json(jp, collect_status(root))
            print(f"wrote {jp}")
            return 0
        # watch loop 2s
        print(f"watch 2s -> {jp} (Ctrl+C to stop)")
        try:
            while True:
                atomic_json(jp, collect_status(root))
                time.sleep(2)
        except KeyboardInterrupt:
            return 0
    # http mode
    host = "127.0.0.1"
    port = args.port
    # also write json once on start
    jp = Path(args.json_path)
    if not jp.is_absolute():
        jp = root / jp
    try: atomic_json(jp, collect_status(root))
    except: pass
    httpd = HTTPServer((host, port), Handler)
    actual = httpd.server_address[1]
    print(f"dashboard http://{host}:{actual}  json {jp}  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0

if __name__ == "__main__":
    sys.exit(main())
