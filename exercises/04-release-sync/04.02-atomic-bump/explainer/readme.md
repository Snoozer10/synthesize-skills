# Exercise 04.02: Atomic Version Bump — Explainer

## Why Atomic Bumps Matter

Version bumps touch **5+ files simultaneously**. Partial updates cause:
- **Drift:** Some files at new version, others at old
- **Broken releases:** npm publishes with mismatched metadata
- **CI confusion:** Validation passes on old code, fails on new

## Atomicity Guarantees

The `release_sync.py --bump` command provides:

| Guarantee | Mechanism |
|-----------|-----------|
| **All-or-nothing** | All files written via temp files in `.git/`, then `os.replace()` |
| **Durability** | `fsync()` on file + directory after each write |
| **Rollback on failure** | Original bytes saved in memory; restored on any post-write failure |
| **Validation gate** | Pre-check (before write) + post-check (after write) |
| **Git safety** | Requires clean working tree; refuses if `VERSION` gitignored |

## Files Updated in Single Transaction

| File | Changes |
|------|---------|
| `VERSION` | `1.0.0` → `1.0.1` |
| `package.json` | `"version": "1.0.0"` → `"version": "1.0.1"` |
| `GEMINI.md` | `version: "1.0.0"` → `version: "1.0.1"`<br>`last_indexed: "2026-09-09"` → `last_indexed: "2026-09-14"` |
| `README.md` | `<!-- release-sync:start -->\nVersion: 1.0.0\n<!-- release-sync:end -->` → `Version: 1.0.1` |
| `CHANGELOG.md` | Unchanged (must have `## [Unreleased]` pre-existing) |

## Rollback Triggers

Rollback occurs if **any** post-write check fails:
- `validate.py` fails (skill validation broken)
- File write fails (permissions, disk full)
- `fsync` fails
- Version parsing fails

## Semver Bump Rules

| Kind | 1.0.0 → |
|------|---------|
| `major` | 2.0.0 |
| `minor` | 1.1.0 |
| `patch` | 1.0.1 |

## Dry-Run Mode

```bash
python scripts/release_sync.py --bump patch
# Output: "would bump 1.0.0 -> 1.0.1 (use --apply to write)"
# Exit 0, no files modified
```

## Pre-Commit Hook Integration

```bash
python scripts/release_sync.py --install-hooks
# Installs .git/hooks/pre-commit running `release_sync.py --check`
```

## Related Exercises

- `04.01-drift-detection` — Tests drift detection (read-only)
- `03.02-closing-loopholes` — Tests validation rule enforcement