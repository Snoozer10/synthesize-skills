# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [1.1.1] - 2026-09-23

> [!NOTE]
> **Patch Maintenance Release**: Comprehensive skills diagnostic and hardening pass. Hardened parity and spec gates against bypass loopholes, achieved 0-warning static analysis across all canonical skills, resolved Windows cp1256 console crashes, decontaminated domain keywords, and wired real execution benchmarks.

### Fixed
- **Strict Parity Gate Bypass (`repo-blast-radius-sync`)**: Hardened `verify_parity.py` to exit 1 when `max_src > mtime` under `--strict` mode.
- **Git Rename Path Parsing (`repo-blast-radius-sync`)**: Fixed `-z` diff parser to preserve new destination path instead of overwriting with old deleted origin.
- **Anti-Premature Completion Loophole (`repo-standards-engineer`)**: Fixed `verify_spec.py` to exit 1 on missing contract or zero evaluated assertions (`assertions: []`), requiring `--allow-empty` for exceptions.
- **Windows Console & Subprocess Crashes (`cp1256` / `cp1252`)**: Reconfigured `sys.stdout`/`sys.stderr` streams to UTF-8 on entry and specified `encoding="utf-8", errors="replace"` in all subprocess calls across `verify_spec.py`, `verify_parity.py`, `check.py`, and `bump.py`.
- **Cross-Platform Tree Hashing (`repo-standards-engineer`)**: Used relative POSIX paths (`p.relative_to(root).as_posix()`) in `discover_standards.py` to ensure identical SHA-256 cache values across Windows and POSIX.
- **Git Worktree Hook Installation (`release-sync`)**: Resolved hook directory dynamically via `git rev-parse --git-dir` + `/hooks` and isolated atomic writes to `target.parent`.
- **Text & Encoding Hygiene**: Removed all double-encoded UTF-8 mojibake (`â€”`, `â†’`) in `SKILL.md` files.

### Changed
- **Validator Compliance (Zero Warnings)**: Refactored `SKILL.md` frontmatter across all skills (`gemini-context-engineer`, `release-sync`, `repo-blast-radius-sync`, `repo-standards-engineer`, `templates/skill-template`) with clean `Use when...` triggers, explicit `## Keywords` sections, and purged workflow summary warnings.
- **Domain Decontamination (`gemini-context-engineer`)**: Replaced hardcoded audio/video terms in `context_compiler.py` with generic semantic keyword overlap.
- **Evaluation Rigor (`gemini-context-engineer`)**: Replaced stub benchmark functions in `run_evals.py` with real script invocations.

---

## [1.1.0] - 2026-09-22

> [!NOTE]
> **Major Feature Release**: Universal Multi-Host Installer Engine, 
repo-standards-engineer skill, Multi-Host Adapter Compiler, and full test suite. Dual-registry publish live on npmjs.org + GitHub Packages with SLSA provenance.

---

### Added
- **Universal Multi-Host Installer Engine** (`install.ps1`, `install.sh`)
  - Cross-platform support across 8 AI host ecosystems: Open Agents Standard, Antigravity/Gemini, Claude Code, OpenAI Codex, OpenCode, Cursor, Windsurf, Copilot.
  - Project and Global installation scopes (`-Scope Project|Global`).
  - Safe concurrency: lock-file acquisition with wait-retry loop and stale-lock recovery.
  - Fail-safe atomic file swaps: staging buffer (`.tmp.<pid>`) before atomic rename.
  - SHA-256 idempotency: zero file churn on identical content.
  - Automatic transaction receipt recording (`.runtime/installed_receipt.json`) and instant clean rollback (`-Rollback` / `--rollback`).
  - Automatic bytecode filtering: excludes `__pycache__` and `*.pyc` files from distribution.
- **Canonical Skill: `rrepo-standards-engineer`** (`.agents/skills/rrepo-standards-engineer/`)
  - AST-based standards discovery (`scripts/discover_standards.py`) extracting API response envelopes, error enums (including `AnnAssign`), and DB query patterns with content-addressed SHA-256 caching.
  - JIT MIP token bounding (`scripts/inject_standards.py`) enforcing $\le 600$ token ceiling.
  - Symbol and standards indexer (`scripts/index_standards.py`).
  - Spec Shaper (`scripts/shape_spec.py`) producing durable `specs/<slug>/SPEC.md` and `VERIFICATION.json`.
  - Executable Verification Contract (`scripts/verify_spec.py`) validating deterministic acceptance assertions before completion (with worktree support).
- **Multi-Host Adapter Compiler** (`scripts/compile_adapters.py`)
  - Compiles native adapters for Claude Code (`.claude/commands/`), Cursor (`.cursor/rules/*.mdc`), Antigravity (`.gemini/rules/`), OpenCode (`.opencode/commands/`), OpenAI Codex (`.codex/instructions/`), and Windsurf (`.windsurf/rules/`).
- **Test & Validation Suite**
  - `tests/test_standards_engine.py` (AST discovery, token bounding, spec verification).
  - `tests/test_installer_concurrency_rollback.py` (PowerShell & pure POSIX shell rollback and bytecode exclusion).
  - `tests/test_compile_adapters.py` (CLI flags, multi-host generation).
  - `tests/test_edge_cases_and_fault_injection.py` (empty directories, token trimming, contract assertion failures).

---

## Release v1.0.1 (2026-09-14)

> [!NOTE]
> **Consolidated Milestone Release**: OIDC dual-registry publishing, comprehensive documentation audit, release-sync exercises, and atomic version parity gate.

---

### 🌟 Executive Summary

This release establishes **production-grade OIDC trusted publisher workflows** for dual-registry publishing (npmjs.org + GitHub Packages) with SLSA Level 1 provenance attestations. It completes a full documentation audit adding error catalog, handoff templates, continuity ledger, and 4 exercise modules (12 pressure scenarios). The release-sync skill is now portable and self-contained with atomic semver bumping across 5 files with rollback guarantees.

---

### 📋 What's Changed in v1.0.1 (2026-09-14)

#### Added

- **OIDC Release Workflow** (`.github/workflows/release.yml`)
  - Dual-registry publish on `v*` tags: npmjs.org + GitHub Packages
  - SLSA Level 1 provenance attestations via `--provenance` flag
  - GitHub Packages uses `GITHUB_TOKEN` with `packages: write` permission
  - npmjs.org uses `NPM_TOKEN` secret (automation token required, not personal token with 2FA)
  - Parallel jobs after validation gate: `validate` → `publish-npm` + `publish-github`

- **Documentation Suite**
  - `docs/error-solving/understood-errors.md` — 15+ known error patterns with resolutions (EOTP, drift, validation, tag force-push, etc.)
  - `docs/handoff.md` — Session handoff template for seamless agent continuity
  - `CONTINUITY.md` — Project state ledger (Done/Now/Next, architecture decisions, learnings)
  - `exercises/04-release-sync/` — 2 pressure scenarios: drift detection (04.01) and atomic bump (04.02)

- **Portable release-sync Skill** (`.agents/skills/release-sync/`)
  - Self-contained: `scripts/check.py` + `scripts/bump.py` (stdlib only, no root script dependency)
  - Atomic semver bump across 5 files: `VERSION`, `GEMINI.md`, `package.json`, `README.md` region, `CHANGELOG.md`
  - Rollback on validation failure or git dirty state
  - 80/20 drift gate: FAIL only on version parity, WARN on hygiene

- **Validation & CI Enhancements**
  - `test_release_sync_pressure.py` — 2 new pressure test scenarios (drift detection, dry-run bump)
  - `test_release_sync_smoke.py` — End-to-end smoke tests for release-sync
  - `validate.yml` PR gate: runs `release_sync.py --check` + `git diff --exit-code`

- **Learning & Process**
  - `GEMINI.md` updated to v1.0.1, `last_indexed: 2026-09-14`, added LEARNING-002 through LEARNING-006
  - `README.md`: GitHub Packages badge, dual-registry install instructions, provenance note
  - `docs/plan/` — 3 new implementation plans (blast-radius JSON fix, proofread, superpowers dashboard)
  - `docs/superpowers/` — Plans and specs for blast-radius enhance + dashboard B live

#### Changed

- **Package Identity**: `@snoozer/creating-ai-agent-skills` → `@snoozer10/synthesize-skills` (aligns with GitHub org)
- **Release Automation**: `npm version patch` + `git push --follow-tags` now triggers OIDC publish (replaces manual `npm publish`)
- **README Badges**: Updated version badge to 1.0.1, added GitHub Packages release badge
- **Skill Catalog**: Now documents all 3 canonical skills with triggers and install commands

#### Verified

- `python scripts/validate.py` → Exit 0 (all 3 skills + template + installed copies)
- `python scripts/release_sync.py --check` → Exit 0 (no version drift across 5 files)
- `python scripts/manifest.py` → manifest.json generated with 3 skills
- `python tests/test_release_sync_pressure.py -v` → Both pressure scenarios pass
- GitHub Actions `validate.yml` → Passes on Windows + Ubuntu (Python 3.11)
- Git tag `v1.0.0` force-updated to HEAD (6abc390) and pushed to origin
- Dual-registry publish verified: `@snoozer10/synthesize-skills@1.0.0` live on both npmjs.org and GitHub Packages with provenance

#### Fixed

- **EOTP Error**: Documented npm automation token requirement (personal tokens with 2FA fail in CI)
- **Tag Drift**: Force-push workflow documented for updating existing tags to new commits
- **Validation Edge Cases**: Added warnings for description format, first-person, workflow summaries, keywords, @-links
- **Read-Only Zone Enforcement**: `Research and docs/` and `The Created Skills/` excluded from edits but still validated locally

---

## Release v1.0.0 (2026-09-09)

> [!NOTE]
> **Foundation Release**: Initial public release with 3 canonical skills, validation pipeline, RED-GREEN-REFACTOR workflow, and npm marketplace presence.

---

### 🌟 Executive Summary

First stable release establishing the synthesize-skills workspace: a standardized framework for authoring, validating, and installing reusable AI-agent skills across 4 host platforms (OpenCode, Claude Code, Gemini CLI, Generic). Includes 3 production skills, comprehensive validation, and automated npm publishing.

---

### 📋 What's Changed in v1.0.0 (2026-09-09)

#### Added

- **Canonical Skills** (`.agents/skills/`)
  - `gemini-context-engineer` — GEMINI.md creation, JIT context compiler (≤600 tokens), VCS AST delta daemon (<100ms), executable workstream proofs
  - `repo-blast-radius-sync` — Blast radius detection, parity verification, live dashboard (port 8765), 4 scripts + 72-line SKILL.md
  - `release-sync` — Version parity gate, atomic semver bump, portable check/bump scripts

- **Validation Pipeline** (`scripts/validate.py`)
  - ERROR (exit 1): name regex, dir==name, description length, frontmatter size, body lines, runnable code fence
  - WARN (exit 0): description starts with "Use when", no first-person, no workflow summary, Keywords required, no @-links

- **Install System**
  - `install.ps1` (Windows) + `install.sh` (POSIX) — SHA256 compare, `.bak` backup, dry-run by default
  - `scripts/manifest.py` — Generates `manifest.json` mapping skills → 4 host dirs
  - Installs to `.agents/skills/`, `.claude/skills/`, `.opencode/skills/`, `.gemini/skills/`

- **RED-GREEN-REFACTOR Workflow** (`docs/WORKFLOW.md`)
  - Stop-gate: one skill at a time, pressure test first (RED), minimal skill (GREEN), close loopholes (REFACTOR)
  - Exercises: 3 modules (skill-authoring, pressure-testing, validation) with 9 scenarios

- **CI/CD** (`.github/workflows/validate.yml`)
  - Matrix: Windows + Ubuntu, Python 3.11
  - Gate: `python scripts/validate.py` must exit 0

- **npm Marketplace Package**
  - `bin/repo-sync.js` — CLI entry: `repo-sync add <skill>`, `repo-sync dashboard --port 8765 --open`
  - `files` allowlist (53 entries), `publishConfig.access: public`

- **Repo Meta**: README, CONTRIBUTING, WORKFLOW, .gitignore, VERSION, LICENSE, CHANGELOG

#### Changed

- **Package Rename**: `@snoozer/creating-ai-agent-skills` → `@snoozer10/synthesize-skills`
- **Repo Migration**: `Snoozer10/synthesize-skills` (new GitHub org alignment)

#### Verified

- All 3 skills pass validation (ERROR=0, WARN=3 per skill)
- Install scripts copy to 4 host dirs with SHA256 dedup
- Manifest.json maps all 3 skills correctly
- CI passes on Windows + Ubuntu

---

### Template for Future Releases

```markdown
## Release v[X.Y.Z] (YYYY-MM-DD)

> [!NOTE]
> **Consolidated Milestone Release**: [One-line summary of theme]

---

### 🌟 Executive Summary

[2-3 sentences on what this release delivers and why it matters]

---

### 📋 What's Changed in v[X.Y.Z] (YYYY-MM-DD)

#### Added
- [Feature/category]: [Description with key files/commands]

#### Changed
- [What changed]: [From → To, with rationale]

#### Verified
- [Command/test]: [Expected result]

#### Fixed
- [Bug]: [Root cause and fix]

#### Removed
- [What was removed]: [Why]
```