# Exercise 04.01: Drift Detection — Baseline Failure

## Problem

The `release_sync.py --check` command should detect version drift between `VERSION`, `package.json`, and `GEMINI.md`.

Create a scenario where:
1. `VERSION` says `1.0.0`
2. `package.json` says `1.0.1`
3. `GEMINI.md` says `version: "1.0.2"`

Run `python scripts/release_sync.py --check` and verify it:
- Exits with code 1
- Reports all three drift errors
- Does NOT modify any files

## Expected Failure Output

```
drift: VERSION 1.0.0 != GEMINI.md version 1.0.2
drift: VERSION 1.0.0 != package.json version 1.0.1
```

## Files to Modify (for test setup only)

- `VERSION` — change to `1.0.0`
- `package.json` — change version to `1.0.1`
- `GEMINI.md` — change version to `1.0.2`

## Verification

```bash
python scripts/release_sync.py --check
# Should exit 1 with drift messages above
```