# Exercise 04.01: Drift Detection — Explainer

## Why Drift Detection Matters

Version drift between `VERSION`, `package.json`, and `GEMINI.md` causes:
- **Broken releases:** npm publishes wrong version
- **Confused users:** Documentation shows different version than installed
- **CI failures:** Automated workflows expect consistency

## How release_sync.py Detects Drift

The `--check` command performs **read-only** verification:

1. **Reads all three sources:**
   - `VERSION` file (single line, plain semver)
   - `package.json` → `version` field (JSON)
   - `GEMINI.md` → `version: "x.y.z"` (YAML frontmatter)

2. **Compares pairwise:**
   - VERSION vs GEMINI.md
   - VERSION vs package.json
   - (GEMINI.md vs package.json implied)

3. **Validates semver format:**
   - Must match `^\d+\.\d+\.\d+$`
   - No pre-release/build metadata in core version

4. **Checks auxiliary drift:**
   - `CHANGELOG.md` has `## [Unreleased]`
   - `README.md` has `<!-- release-sync:start -->` region
   - `GEMINI.md` `last_indexed` not stale (>90 days)
   - `GEMINI.md` rules match `PINS` constant
   - `VERSION` not gitignored
   - `scripts/validate.py` passes

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No drift — all checks pass |
| 1 | Drift detected — version mismatch or auxiliary failure |
| 2 | Usage error — invalid arguments |

## Design Principles

- **Read-only:** `--check` never writes files
- **Fail-closed:** Missing markers = drift (e.g., no `## [Unreleased]` = fail)
- **Single source of truth:** `VERSION` file is canonical; others must match
- **Atomic bump:** `--bump patch --apply` updates all files in one transaction with rollback on failure

## Related Exercises

- `04.02-atomic-bump` — Tests atomic version bump with rollback
- `03.01-validate-rules` — Tests skill validation drift