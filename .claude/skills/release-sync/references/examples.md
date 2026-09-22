# release-sync Examples

## Check for drift (read-only)

```bash
python .agents/skills/release-sync/scripts/check.py
```

Exit 0 = clean. Exit 1 = drift. Stderr shows details.

## Check with JSON output

```bash
python .agents/skills/release-sync/scripts/check.py --json
```

Returns `{"status":"clean|drift","version":"1.0.0",...}`.

## Dry-run bump (no writes)

```bash
python .agents/skills/release-sync/scripts/bump.py patch
```

Output: `would bump 1.0.0 -> 1.0.1`. No files changed.

## Apply bump (writes 3 files)

```bash
python .agents/skills/release-sync/scripts/bump.py patch --apply
```

Writes VERSION, GEMINI.md, package.json atomically. Rolls back on failure.

## Bump major/minor

```bash
python .agents/skills/release-sync/scripts/bump.py minor --apply
python .agents/skills/release-sync/scripts/bump.py major --apply
```

## Use in CI (pre-commit or PR gate)

```yaml
# .github/workflows/validate.yml
- run: python .agents/skills/release-sync/scripts/check.py
```
