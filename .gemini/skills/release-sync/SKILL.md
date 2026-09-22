---
name: release-sync
description: "Use when VERSION, GEMINI.md, or package.json versions may drift, when CHANGELOG/README hygiene is needed, or before bumping major|minor|patch — parity gate and atomic bump for release_sync"
---

# release-sync

## Overview
- Parity gate: detects version drift across VERSION, GEMINI.md, and package.json.
- Atomic bump: writes all three files with rollback on failure.

## When to Use
- Before committing version changes or release prep
- CI drift detection (exit 1 blocks push)
- Bumping major|minor|patch version
- When NOT to use: unrelated code edits, no version files present

Keywords: version, drift, parity, semver, bump, release, VERSION, GEMINI.md, package.json

## Quick Reference
| Situation | Action |
|-----------|--------|
| Check for drift | `python .agents/skills/release-sync/scripts/check.py` |
| Dry-run bump | `python .agents/skills/release-sync/scripts/bump.py patch` |
| Apply bump | `python .agents/skills/release-sync/scripts/bump.py patch --apply` |
| JSON output | Add `--json` to any command above |
| Exit code 0 | Clean (no drift) |
| Exit code 1 | Version drift detected |
| Exit code 2 | Usage error (bad args or invalid semver) |

## Implementation
1. Run check to detect drift:
   ```bash
   python .agents/skills/release-sync/scripts/check.py
   ```
2. If drift, fix VERSION/GEMINI.md/package.json to match, then re-check.
3. To bump, dry-run first, then apply:
   ```bash
   python .agents/skills/release-sync/scripts/bump.py patch
   python .agents/skills/release-sync/scripts/bump.py patch --apply
   ```

```python
import sys
sys.path.insert(0, ".agents/skills/release-sync/scripts")
from check import check
assert check(as_json=True) in (0, 1), "check exits 0 or 1"
print("PASS")
```

## Common Mistakes
- Editing VERSION by hand without updating GEMINI.md. Fix: use bump.py.
- Running bump without --apply and expecting writes. Fix: add --apply.
- Skipping pre-check drift. Fix: bump.py runs check.py automatically.

## References
- Exit codes, bump matrix, PINS: [references/api.md](references/api.md)
- Copy-paste commands: [references/examples.md](references/examples.md)
