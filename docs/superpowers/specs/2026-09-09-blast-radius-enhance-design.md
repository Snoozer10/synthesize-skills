# Design: repo-blast-radius-sync — Lean Expansion (Approach B)

**Date:** 2026-09-09
**Status:** Draft → Review (Rev 1 after grill)
**Scope:** Promoted skill `.agents/skills/repo-blast-radius-sync` (4 scripts + SKILL.md + eval/CI snippets). No monorepo perf work (Approach C deferred).
**Precedent:** 3-subagent brainstorm (DX / Robustness / Testing), ponytail ladder, writing-for-agents hierarchy. Grill 7/7 FAIL → fixes below.

## 1. Goal

Make zero-orphan gate checkable and adoption-ready without growing `SKILL.md` context load. Current gate works but has silent false PASS/FAIL on `path with spaces`, rename, Windows `\`, binary files, and premature completion is possible (agent declares done while `verify_parity --strict` exit 1).

## 2. Architecture (1 clear purpose per unit)

- **`build_registry.py`** — compile: walk repo, parse `ast` imports + `@docs/@tests/@governs` regex via `Path.as_posix()`, write sorted `registry.json` (keys posix `a/b.py`). No incremental cache yet — `__pycache__` excluded, `skipped[]` logged for binary/large. Canonical: `registry keys = Path.relative_to(root).as_posix()`, `dirty_files = PurePosixPath(git_path).as_posix()` where `git_status -z` already posix.
- **`blast_radius.py`** — query: load registry or ephemeral `scan_workspace_dynamically()` (sorted, `.agent` excluded), resolve `CODE_CALLERS / GOVERNING_DOCS / TEST_SUITES / CONFIGS` with stable leading words `CODE_CALLERS:`, `GOVERNING_DOCS:`, `TEST_SUITES:`, `CONFIGS:` at column 0 for `grep "^GOVERNING_DOCS:"`. Supports both `--json` (machine) and default text (human) — both canonical.
- **`verify_parity.py`** — gate: `git status --porcelain=v1 -z` NUL split → `dirty_files` (quoted/unquoted + `R100 old\0new` NUL pair + `??`/`AM`/`AD` with spaces). Compare radius vs staged/dirty, emit `ERR_ORPHAN_EDIT_VIOLATION` JSON envelope to stderr. `--strict` adds `CONFIGS/CALLERS`; tagged `@governs/@docs/@tests` → `ERR`, untagged heuristic → `WARN` (advisory, not blocking). Blocks if `max(source mtime) > registry mtime` with `ERR_STALE_REGISTRY`.
- **`draft_doc_updates.py`** — heal: `git diff HEAD -- *.py` `+def foo(...):` excerpt → `## AUTOMATED INTERFACE UPDATE` append block, supports `--dry-run` preview (stdout, exit code preserved, no FS write).
- **`references/`** — disclosed schema/examples (`registry_schema.json` + `*.example`) behind pointer `Need schema? Load references/...`, keeps `SKILL.md` <150 lines. **Not disclosed:** 2-line hard gate `Before declaring done: python scripts/verify_parity.py --strict` + `ERR_ORPHAN_EDIT_VIOLATION` block — always inline (prevents premature completion).
- **`tests/test_blast_radius_parity.py`** — **single source of truth** completion criterion: hermetic `setup_clean_repo` (like `tests/test_release_sync_smoke.py`) asserts `verify_parity --strict exit 0` + `staged ⊇ (GOVERNING_DOCS ∪ TEST_SUITES)` + `staged ∋ registry.json if dirty` + `registry mtime >= max(source mtime)` (or `sha256(registry) == sha256(rebuild)`) + no lexical `TODO`.

Interfaces: `scripts/*` invoked via `python scripts/<tool> --help` (stdlib `argparse` epilog holds examples). Ordered sequence: `1 build_registry --root . → 2 blast_radius <target> [--json|--symbol] → 3 edit+git add → 4 build_registry → 5 verify_parity --strict` (hard pull before done).

## 3. Components & Changes

| Area | File | Change | Tokens |
|------|------|--------|--------|
| Correctness | `verify_parity.py:23 get_dirty_git_files()` | Replace `line[3:].strip()` + `->` split with `-z` NUL split, handle quotes + octal via `core.quotepath` decode, map `R100 old\0new`, `??`/`AM`/`AD`/`"a b.py"` with spaces; fallback to line mode if `git <2.8` missing `-z` with `WARN: legacy porcelain` + quote-aware parse (or `exit 2 ERR_GIT_TOO_OLD`) | ~15 lines |
| Robustness | `build_registry.py:77` + `blast_radius.py:75` `scan_*` | Guard `if stat.st_size > 5MiB or b'\x00' in head(8k): skip` before `read_text()`; catch `UnicodeDecodeError`; allowlist `.py,.md,.json,.yaml,.toml,.ini,.cfg,.js,.ts` + log skipped to `registry.json:skipped[]` with `WARN` | 6 lines |
| DX | `blast_radius.py:175` + `verify_parity.py:141` `argparse` | Add `epilog="Example: ..."` + `--dry-run` (exit code preserved, stdout) to `draft_doc_updates`/`verify_parity` + `CODE_*: GOVERNING_DOCS:` prefix; `--json/--symbol` surfaced in Quick Ref | 10 lines |
| Docs | `SKILL.md:21` Quick Ref | Add row `For agents: ... --json / --symbol <F> --json`, pointer `Need schema? Load references/...`, posix contract `Paths: posix a/b.py — \ auto-normalized via as_posix()` | +15/-5 tokens |
| Testing | `tests/test_blast_radius_parity.py` (new, ~80 lines) | Stdlib hermetic at repo root `tests/` (per `docs/WORKFLOW.md` RED), asserts `verify_parity --strict exit 0` + `staged ⊇ GOVERNING_DOCS∪TEST_SUITES` + `staged ∋ registry` + `sha256 fresh` + no `TODO` | +80 |
| Evals | `evals/eval_scenarios.json` | 3→6 scenarios: `deleted_caller`, `schema_key_rename`, `todo_deferral_trap`; `pass_criteria` maps to `verify_parity_exit==0 && staged ⊇ GOVERNING_DOCS∪TEST_SUITES` | +30 |
| CI/version | `docs/blast-radius.yml` + `VERSION` | Snippet: `python scripts/validate.py && python scripts/build_registry.py && python scripts/verify_parity.py --strict` on `windows-latest+ubuntu-latest`; bump `VERSION 0.1.1→0.1.2` + `release_sync --check` in proof | 15 lines md |

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

- `registry.json` stale: `ERR_STALE_REGISTRY` if `max(source mtime) > registry mtime` or `sha256 mismatch` → block `verify_parity --strict` (not just warn) — ordered gate prevents stale PASS.
- `git status -z` parse: try NUL; fallback to line mode with quote-aware octal decode via `core.quotepath`; if still ambiguous emit `WARN: legacy porcelain` and parse correctly or `exit 2 ERR_GIT_TOO_OLD` (ponytail: fail > silent wrong) — tested on `windows-latest` with `path with spaces` + `R100` rename fixtures.
- Binary/large skip: `WARN: skip large/binary a/b.py` to stderr + record in `registry.json:skipped[]`; not failure, auditable. Catch `UnicodeDecodeError` via 8k head check.
- `draft --dry-run` + `verify_parity --dry-run`: print patch/JSON to stdout, preserve exit code, no FS write.

## 6. Testing (RED→GREEN→REFACTOR per docs/WORKFLOW.md)

- **RED:** add 3 scenarios to `eval_scenarios.json`, run `python tests/test_blast_radius_parity.py` without skill — expect `docs_synchronized=false`, `verify_parity_exit==1`, `TODO` present → recorded verbatim.
- **GREEN:** minimal `SKILL.md` + 4 scripts as above, re-run — `docs_synchronized=true`, `exit 0`, `registry fresh` → agent complies.
- **REFACTOR:** add `TODO trap` + `stale-registry` counters to harness `defects[]`, re-verify, keep `SKILL.md` token-flat via disclosure.

Proof command (workstream gate): `python scripts/validate.py && python scripts/release_sync.py --check && python tests/test_blast_radius_parity.py -v` (bump `VERSION 0.1.1→0.1.2` before proof).

## 7. Disclosure / Load Budget

- Context load: `SKILL.md` stays under `validate.py:68-69` body<500 (499 max) / frontmatter raw≤1024 (currently 68 lines/245 raw). Disclosure moves schema/examples behind `references/` pointer; post-completion steps hidden via **sequence split** (ordered 1→5 gate) not inline disclosure — hard pull `verify_parity --strict` stays inline to block premature completion.
- Cognitive load: human faces one CI snippet + one test file, not per-tool docs. No new `agents/` subagent scaffolding.

## 8. Out of Scope (Approach C, when measured)

- Incremental `mtime+sha256` registry, LRU memo, `--scope` sharding, `scripts/doctor.py`. Trigger: `build_registry >1s` or `registry.json >5MB` or `>10k` repeated blast queries (benchmark first).

## 9. Risks

- `-z` quote handling differs per git version → dual-path + `8k` head + Windows `path with spaces` + `R100` fixtures on `windows-latest`/`ubuntu-latest` (`validate.yml:16`).
- Generic heuristic `WARN` (untagged) vs `ERR` (tagged `@governs/@docs/@tests` or `ast` imports) — intentional to avoid sprawl ghost docs; `WARN` still in `defects[]` and `skipped[]`, auditable via future `doctor`.

## 10. References

- `scripts/validate.py:6-82` name/regex/runnable/warn rules
- `scripts/release_sync.py:13 PINS` stdlib-only
- `AGENTS.md: Repo truth` SSOT + `docs/WORKFLOW.md` stop-gate
