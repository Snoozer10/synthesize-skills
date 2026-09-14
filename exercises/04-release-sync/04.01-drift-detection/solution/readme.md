# Exercise 04.01: Drift Detection — Solution

## Solution

The `release_sync.py --check` command already implements drift detection. No code changes needed — this exercise verifies the existing behavior.

## Verification Steps

1. **Set up drift scenario:**
   ```bash
   echo "1.0.0" > VERSION
   # Edit package.json version to 1.0.1
   # Edit GEMINI.md version to 1.0.2
   ```

2. **Run drift check:**
   ```bash
   python scripts/release_sync.py --check
   ```

3. **Verify exit code 1 and drift messages:**
   ```
   drift: VERSION 1.0.0 != GEMINI.md version 1.0.2
   drift: VERSION 1.0.0 != package.json version 1.0.1
   ```

4. **Restore correct versions:**
   ```bash
   python scripts/release_sync.py --bump patch --apply
   # Or manually sync all three files
   ```

## Key Implementation (in release_sync.py)

The `do_check()` function compares:
- `read_version(root)` → `VERSION` file
- `read_package_version(root)` → `package.json` version field
- `read_gemini(root)` → `GEMINI.md` version field

All three must match exactly, or drift is reported and exit code 1 returned.

## Test Command

```bash
python scripts/release_sync.py --check
# Exit code: 1 (drift detected)
# Stdout: drift messages
```