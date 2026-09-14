# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [Unreleased]

> Next release will include: npm automation token configuration for CI, next skill development cycle (RED-GREEN-REFACTOR), and any community contributions.

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