---
name: repo-blast-radius-sync
description: Use when modifying, refactoring, adding features, or fixing bugs in code, scripts, schemas, or configs where callers, tests, or docs must stay in sync — detects blast radius and blocks orphaned commits
---

# repo-blast-radius-sync

## Overview
- Zero-orphan gate: edits to source, schema, or API must include coupled docs, tests, and callers in staged changes.
- Every change has a blast radius: callers, configs, tests, and docs that must stay in sync.
- Gate `scripts/verify_parity.py` blocks commit when orphans remain; `scripts/blast_radius.py` discovers them pre-flight. Before declaring done: `python scripts/verify_parity.py --strict` must exit 0 or `ERR_ORPHAN_EDIT_VIOLATION`/`ERR_STALE_REGISTRY` in stderr blocks.

## When to Use
- Modifying, refactoring, adding features, or fixing bugs in code, scripts, schemas, or configs
- Changing signatures, config keys, or API contracts with downstream callers
- Updating tests or reference docs that may drift from implementation
- When NOT to use: isolated typo with no code coupling, or one-off note outside blast radius

Keywords: orphan, blast radius, verify_parity, blast_radius.py, staged, parity gate, build_registry.py, draft_doc_updates.py

## Quick Reference
| Situation | Action |
|-----------|--------|
| Before editing | Run `python scripts/blast_radius.py <path> [--json] [--symbol <Func>]` and grep `^GOVERNING_DOCS:` `^CODE_CALLERS:` |
| During edits | Update target plus all coupled files, tests, and docs |
| Before commit | Run `python scripts/build_registry.py` then `python scripts/verify_parity.py --strict [--dry-run]` |
| Gate fails (exit 1) | Run `python scripts/draft_doc_updates.py <doc> [--dry-run]`, stage, rebuild and re-verify |
| Need schema? | Load `references/registry_schema.json` or `references/*.example` (disclosed) |
| Paths | Always posix `a/b.py` — `\` auto-normalized via `as_posix()` |
| Optional audit | Append ledger entry if team requires it (see references/) |

## Implementation
1. Pre-flight discovery
   - `python scripts/blast_radius.py <target_file_path>` e.g. `python scripts/blast_radius.py src/payments/processor.py`
   - Read checklist categories: CODE CALLERS, GOVERNING DOCS, TEST SUITES, CONFIGS/SCHEMAS
2. Cascading mutation
   - Edit target file for objective
   - Align callers in CODE CALLERS
   - Sync keys in CONFIGS/SCHEMAS
   - Update pytest cases in TEST SUITES
   - Refine manuals in GOVERNING DOCS
3. Parity gate and self-healing
   - Compile and verify:

```bash
python scripts/build_registry.py
python scripts/verify_parity.py --strict
```

   - Exit 0: synchronized, commit allowed
   - Exit 1: parse stderr, run `python scripts/draft_doc_updates.py <coupled_doc_path>` (e.g. `docs/api_reference.md`), `git add` doc, rebuild registry and re-verify until 0

4. Verify runnable check

```python
def blast_radius_contains(radius, expected):
    return expected in radius.get("GOVERNING DOCS", []) or expected in radius.get("TEST SUITES", [])

if __name__ == "__main__":
    sample = {"GOVERNING DOCS": ["docs/api_reference.md"], "TEST SUITES": ["tests/test_processor.py"], "CODE CALLERS": [], "CONFIGS/SCHEMAS": []}
    assert blast_radius_contains(sample, "docs/api_reference.md")
    assert not blast_radius_contains(sample, "docs/missing.md")
    print("PASS")
```

## Common Mistakes
- Declaring task completed while `verify_parity.py` exits 1. Fix: heal docs and re-verify, do not request review.
- Using `# TODO: update documentation later` in code. Fix: update GOVERNING DOCS in same change.
- Modifying or deleting `.agent/` or `scripts/` to bypass gate. Fix: keep gate intact, fix orphans.
- Guessing doc patches manually. Fix: use `scripts/draft_doc_updates.py` from git diff.
