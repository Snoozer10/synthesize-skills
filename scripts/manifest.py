"""Generate manifest.json mapping skill -> host install paths. Stdlib only."""
import json
import sys
from pathlib import Path

HOSTS = [".agents", ".claude", ".opencode", ".gemini"]


def main(argv):
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    canon = root / ".agents" / "skills"
    skills = []
    if canon.is_dir():
        skills = sorted(p.name for p in canon.iterdir() if p.is_dir())
    # include template as documented example, not installed
    manifest = {}
    for name in skills:
        manifest[name] = {h.lstrip("."): ("%s/skills/%s" % (h, name)) for h in HOSTS}
    out = root / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("wrote '%s' with %d skills" % (out, len(manifest)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
