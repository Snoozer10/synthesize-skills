"""Generate manifest.json mapping skill -> host install paths across 7+ AI agent hosts. Stdlib only."""
import json
import sys
from pathlib import Path

HOST_MAP = {
    "agents": ".agents/skills",
    "claude": ".claude/skills",
    "opencode": ".opencode/skills",
    "gemini": ".gemini/skills",
    "codex": ".codex/skills",
    "cursor": ".cursor/skills",
    "windsurf": ".windsurf/skills",
    "copilot": ".copilot/skills",
}


def build_manifest(root: Path) -> dict:
    canon = root / ".agents" / "skills"
    skills = []
    if canon.is_dir():
        skills = sorted(p.name for p in canon.iterdir() if p.is_dir())
    manifest = {}
    for name in skills:
        manifest[name] = {h: f"{prefix}/{name}" for h, prefix in HOST_MAP.items()}
    return manifest


def main(argv):
    root = Path(".")
    out_dir = None

    idx = 1
    while idx < len(argv):
        arg = argv[idx]
        if arg == "--stage-dir" and idx + 1 < len(argv):
            out_dir = Path(argv[idx + 1])
            idx += 2
        elif not arg.startswith("-"):
            root = Path(arg)
            idx += 1
        else:
            idx += 1

    manifest = build_manifest(root)
    dest_dir = out_dir if out_dir else root
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("wrote '%s' with %d skills across %d hosts" % (out, len(manifest), len(HOST_MAP)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
