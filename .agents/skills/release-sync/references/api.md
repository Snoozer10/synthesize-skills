# release-sync API Reference

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Clean (no drift) or dry-run success |
| 1 | Version drift detected or bump failed |
| 2 | Usage error (bad args, invalid semver) |

## 80/20 Rule

**FAIL (exit 1):** Only version parity mismatch:
- `VERSION != GEMINI.md version`
- `VERSION != package.json version`
- `validate.py` non-zero exit
- Invalid semver in VERSION

**WARN (exit 0, stderr):** Everything else:
- PINS mismatch in GEMINI.md rules
- README.md missing release-sync region
- CHANGELOG.md missing `## [Unreleased]`
- `last_indexed` >30d (warn) or >90d (warn)
- Git working tree dirty

## Semver Bump Matrix

| Kind | Input | Output |
|------|-------|--------|
| major | 1.2.3 | 2.0.0 |
| minor | 1.2.3 | 1.3.0 |
| patch | 1.2.3 | 1.2.4 |

## Files Written by bump.py

| File | Field Updated |
|------|---------------|
| `VERSION` | Whole file (new version string) |
| `GEMINI.md` | `version: "X.Y.Z"` + `last_indexed: "YYYY-MM-DD"` |
| `package.json` | `"version": "X.Y.Z"` |

## Atomic Write Guarantee

bump.py uses `tempfile.mkstemp` + `os.replace` + `os.fsync` for crash-safe writes. On any failure (post-check, I/O), all files are rolled back to pre-bump state.
