# Exercise 04.02: Atomic Version Bump — Baseline Failure

## Problem

The `release_sync.py --bump patch --apply` command should atomically update all version files with rollback on failure.

Create a scenario where:
1. All versions start at `1.0.0` (synced)
2. Run `python scripts/release_sync.py --bump patch --apply`
3. Verify it:
   - Updates `VERSION` to `1.0.1`
   - Updates `package.json` version to `1.0.1`
   - Updates `GEMINI.md` version to `1.0.1` and `last_indexed` to today
   - Updates `README.md` release-sync region to `1.0.1`
   - Exits 0 on success

Then create a **failure scenario** where validation fails post-bump:
1. Temporarily break a skill (e.g., remove "Use when" from description)
2. Run `python scripts/release_sync.py --bump patch --apply`
3. Verify it:
   - Rolls back ALL files to pre-bump state
   - Exits 1
   - Reports "validate post-check failed, rolled back"

## Expected Success Output

```
bumped 1.0.0 -> 1.0.1
```

## Expected Failure Output (with broken validation)

```
validate post-check failed, rolled back
```

## Files Involved

- `VERSION`
- `package.json`
- `GEMINI.md`
- `README.md` (release-sync region)
- `CHANGELOG.md` (must have `## [Unreleased]`)

## Verification

```bash
# Success case
python scripts/release_sync.py --bump patch --apply
# Exit 0, all files updated

# Failure case (after breaking a skill)
python scripts/release_sync.py --bump patch --apply
# Exit 1, all files rolled back
```