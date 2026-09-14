# Exercise 04.02: Atomic Version Bump — Solution

## Solution

The `release_sync.py --bump patch --apply` already implements atomic bump with rollback. This exercise verifies the behavior.

## Verification Steps

### Success Case

1. **Ensure clean state:**
   ```bash
   python scripts/release_sync.py --check  # Should pass (exit 0)
   git status  # Should be clean
   ```

2. **Run atomic bump:**
   ```bash
   python scripts/release_sync.py --bump patch --apply
   ```

3. **Verify all files updated:**
   ```bash
   cat VERSION           # 1.0.1
   cat package.json | grep version  # "1.0.1"
   grep 'version:' GEMINI.md  # version: "1.0.1"
   grep 'last_indexed:' GEMINI.md  # today's date
   grep 'Version:' README.md  # Version: 1.0.1 (in release-sync region)
   ```

4. **Verify drift check passes:**
   ```bash
   python scripts/release_sync.py --check  # Exit 0
   ```

### Failure Case (Rollback Test)

1. **Break validation:**
   ```bash
   # Edit a skill to remove "Use when" from description
   sed -i 's/Use when /Invalid /' .agents/skills/release-sync/SKILL.md
   ```

2. **Run bump (should fail and rollback):**
   ```bash
   python scripts/release_sync.py --bump patch --apply
   # Should exit 1 with "validate post-check failed, rolled back"
   ```

3. **Verify rollback:**
   ```bash
   cat VERSION           # Back to 1.0.0
   cat package.json | grep version  # "1.0.0"
   grep 'version:' GEMINI.md  # version: "1.0.0"
   # Skill description restored
   ```

4. **Fix skill and retry:**
   ```bash
   sed -i 's/Invalid /Use when /' .agents/skills/release-sync/SKILL.md
   python scripts/release_sync.py --bump patch --apply
   # Should succeed now
   ```

## Key Implementation (in release_sync.py)

The `do_bump()` function:
1. **Pre-validates:** Runs `validate.py`, checks git clean, checks VERSION not gitignored
2. **Prepares all new content** in memory (VERSION, GEMINI.md, package.json, README.md)
3. **Atomic writes** via `atomic_write()` using temp files in `.git/` dir + `os.replace()` + `fsync`
4. **Post-validates:** Runs `validate.py` again
5. **Rollback on failure:** Restores all original files from saved bytes

## Test Commands

```bash
# Success
python scripts/release_sync.py --bump patch --apply
# Exit 0, "bumped 1.0.0 -> 1.0.1"

# Failure (with broken skill)
python scripts/release_sync.py --bump patch --apply
# Exit 1, "validate post-check failed, rolled back"
```