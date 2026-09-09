# Design: repo-blast-radius-sync — Lean Expansion (Approach B)

**Date:** 2026-09-09
**Status:** Draft → Review
**Scope:** Promoted skill `.agents/skills/repo-blast-radius-sync` (4 scripts + SKILL.md). No monorepo perf work (Approach C deferred).
**Precedent:** 3-subagent brainstorm (DX / Robustness / Testing), ponytail ladder, writing-for-agents hierarchy.

## 1. Goal

Make zero-orphan gate checkable and adoption-ready without growing `SKILL.md` context load. Current gate works but has silent false PASS/FAIL on `path with spaces`, rename, Windows `\`, binary files, and premature completion is possible (agent declares done while `verify_parity --strict` exit 1).

## 2. Architecture (1 clear purpose per unit)

- **`build_registry.py`** — compile: walk repo, parse `ast` imports + `@docs/@tests/@governs` regex, write sorted `registry.json` (keys posix `a/b.py`). No incremental cache yet — `__pycache__` excluded, `as_posix()` canonical.
- **`blast_radius.py`** — query: load registry or ephemeral `scan_workspace_dynamically()` (sorted, `.agent` excluded), resolve `CODE CALLERS / GOVERNING DOCS / TEST SUITES / CONFIGS` with leading words `[CODE CALLERS]` in `print_text_checklist` for grep.
- **`verify_parity.py`** — gate: `git status --porcelain=v1 -z` NUL parse → `dirty_files` (posixed), compare radius vs staged/dirty, emit `ERR_ORPHAN_EDIT_VIOLATION` JSON envelope to stderr. `--strict` adds `CONFIGS/CALLERS`; generic heuristic downgraded to `WARN` advisory.
- **`draft_doc_updates.py`** — heal: `git diff HEAD -- *.py` `+def foo(...):` excerpt → `## AUTOMATED INTERFACE UPDATE` append block, supports `--dry-run` preview.
- **`references/`** — disclosed schema/examples (`registry_schema.json` + `*.example`) behind pointer `Need schema? Load references/...`, keeps `SKILL.md` <150 lines.
- **`tests/test_blast_radius_parity.py`** — completion criterion: hermetic `setup_clean_repo` (like `tests/test_release_sync_smoke.py`) asserts `exit 0` + staged contains `coupled docs/tests` + no `TODO` + `registry mtime > dirty mtime`.

Interfaces: `scripts/*` invoked via `python scripts/<tool> --help` (stdlib `argparse` epilog holds examples). Gate depends on registry file, not on each other.

## 3. Components & Changes

| Area | File | Change | Tokens |
|------|------|--------|--------|
| Correctness | `verify_parity.py:23 get_dirty_git_files()` | Replace `line[3:].strip()` + `->` split with `-z` NUL split, strip quotes, map `R100 old\0new`, handle `??`/`AM`/`AD` | ~15 lines |
| Robustness | `build_registry.py:77` + `blast_radius.py:75` `scan_*` | Guard `if stat.st_size > 1MiB or b'\x00' in head(1k): skip` before `read_text()`; allowlist `.py,.md,.json,.yaml,.toml,.ini,.cfg` | 6 lines |
| DX | `blast_radius.py:175` + `verify_parity.py:141` `argparse` | Add `epilog="Example: ..."` + `--dry-run` to `draft_doc_updates`/`verify_parity` (print without write) + `--json/--symbol` surfaced in SKILL Quick Ref | 10 lines |
| Docs | `SKILL.md:21` Quick Ref | Add row `For agents: ... --json / --symbol <F> --json`, pointer `Need schema? Load references/...`, posix contract line `Paths: posix a/b.py — \ auto-normalized` | +15/-5 tokens |
| Testing | `tests/test_blast_radius_parity.py` (new, ~80 lines) | Stdlib hermetic, asserts checkable RED criteria per `docs/WORKFLOW.md` | +80 |
| Evals | `evals/eval_scenarios.json` | 3→6 scenarios: `deleted_caller`, `schema_key_rename`, `todo_deferral_trap`; `pass_criteria` gains regex keys `docs_synchronized / verify_parity_exit==0` | +30 |
| CI | `docs/blast-radius.yml` (snippet) | Copy-paste workflow: `build_registry` → `verify_parity --strict` + optional `eval_orphaned_edit --report-json` | 15 lines md |

Total delta ~250 LOC, 1 new executable file, rest doc/JSON. No new deps (stdlib `argparse`, `hashlib`, `pathlib`, `subprocess` already used).

## 4. Data Flow

```
blast_radius <target> --json  →  radius{CODE CALLERS, GOVERNING DOCS, TEST SUITES, CONFIGS}  →  checklist
build_registry --root .        →  .agent/registry.json (sorted, posix)
verify_parity --strict [--dry-run]  ←  registry + git status -z  →  exit 1 JSON failures | exit 0 PASS
draft_doc_updates <doc> [--dry-run]  ←  git diff  →  markdown patch
tests/test_blast_radius_parity.py  →  hermetic repo  →  Lazy/Forgetful/Compliant asserts (score 1.0 only if staged sync + registry fresh)
```

## 5. Error Handling

- `registry.json` stale: warn if `max(source mtime) > registry mtime` → `drift: rebuild` (not failure until gate runs).
- `git status -z` parse: fallback to `git status --porcelain=v1` line mode if `git` <2.8 missing `-z`, emit `WARN: legacy porcelain`.
- Binary/large skip: silent skip with `print("[skip] large/binary", file=sys.stderr)` not failure.
- `draft --dry-run`: print patch to stdout, return 0 without touching FS.

## 6. Testing (RED→GREEN→REFACTOR per docs/WORKFLOW.md)

- **RED:** add 3 scenarios to `eval_scenarios.json`, run `python tests/test_blast_radius_parity.py` without skill — expect `docs_synchronized=false`, `verify_parity_exit==1`, `TODO` present → recorded verbatim.
- **GREEN:** minimal `SKILL.md` + 4 scripts as above, re-run — `docs_synchronized=true`, `exit 0`, `registry fresh` → agent complies.
- **REFACTOR:** add `TODO trap` + `stale-registry` counters to harness `defects[]`, re-verify, keep `SKILL.md` token-flat via disclosure.

Proof command (workstream gate): `python scripts/validate.py && python tests/test_blast_radius_parity.py -v`.

## 7. Disclosure / Load Budget

- Context load: `SKILL.md` stays under `validate.py:68` body<500/frontmatter≤1024 (currently 68 lines/245 raw). Disclosure moves schema heavy ref behind `references/` pointer; post-completion steps not shown inline.
- Cognitive load: human faces one CI snippet + one test file, not per-tool docs. No new `agents/` subagent scaffolding.

## 8. Out of Scope (Approach C, when measured)

- Incremental `mtime+sha256` registry, LRU memo, `--scope` sharding, `scripts/doctor.py`. Trigger: `build_registry >1s` or `registry.json >5MB` or `>10k` repeated blast queries (benchmark first).

## 9. Risks

- `-z` quote handling differs per git version → mitigate with dual-path + test on `windows-latest`/`ubuntu-latest` matrix (existing `validate.yml:16`).
- Downgrading generic heuristic to `WARN` may surface legacy untagged code as PASS — intentional, avoids sprawl ghost docs; audit via `doctor` later.

## 10. References

- `scripts/validate.py:6-82` name/regex/runnable/warn rules
- `scripts/release_sync.py:13 PINS` stdlib-only
- `AGENTS.md: Repo truth` SSOT + `docs/WORKFLOW.md` stop-gate
