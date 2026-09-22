# synthesize-skills

[![Version](https://img.shields.io/badge/version-1.0.1-blue)](VERSION)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/Snoozer10/synthesize-skills/validate.yml?branch=main)](https://github.com/Snoozer10/synthesize-skills/actions/workflows/validate.yml)
[![Python](https://img.shields.io/badge/python-3.11+-yellow)](https://www.python.org/)
[![npm](https://img.shields.io/npm/v/@snoozer10/synthesize-skills)](https://www.npmjs.com/package/@snoozer10/synthesize-skills)
[![GitHub Packages](https://img.shields.io/github/v/release/Snoozer10/synthesize-skills?label=github%20packages&color=blue)](https://github.com/Snoozer10/synthesize-skills/packages)

> Workspace for authoring, validating, and installing reusable AI-agent skills. Skills are `SKILL.md` files with YAML frontmatter, validated by `scripts/validate.py`, installed to 4 host dirs (`.agents/skills`, `.claude/skills`, `.opencode/skills`, `.gemini/skills`). RED-GREEN-REFACTOR workflow enforces one skill at a time with pressure-scenario testing before acceptance.

---

## 📦 Skills Catalog (4 Canonical Skills)

| Skill | Description | Trigger | Install |
|---|---|---|---|
| `gemini-context-engineer` | Use when creating or maintaining GEMINI.md, mapping repository architecture, compiling task context slices, guarding git boundaries, or verifying execution contracts | GEMINI.md tasks, repo mapping, context compilation | `repo-sync add gemini-context-engineer` |
| `repo-blast-radius-sync` | Use when modifying, refactoring, adding features, or fixing bugs in code, scripts, schemas, or configs where callers, tests, or docs must stay in sync — detects blast radius and blocks orphaned commits | Refactor/feature/bugfix, parity verification | `repo-sync add repo-blast-radius-sync` |
| `release-sync` | Use when VERSION, GEMINI.md, or package.json versions may drift, when CHANGELOG/README hygiene is needed, or before bumping major\|minor\|patch — parity gate and atomic bump for release_sync | Release prep, version drift detection | `repo-sync add release-sync` |
| `repo-standards-engineer` | Use when extracting codebase standards, response envelopes, and error codes via AST, injecting token-bounded invariants into agent context, shaping interactive specs, or executing deterministic contract verifications | Standards extraction, spec interview, contract verification | `repo-sync add repo-standards-engineer` |

### Skill Details

#### `repo-standards-engineer`
- **Capabilities**: AST Standards Scanner (extracts envelopes, enums, DB patterns with SHA-256 caching), JIT Token Bounding (MIP ≤600 tokens), Spec Shaper (`specs/<slug>/SPEC.md`), Executable Assertion Contracts (`verify_spec.py`).
- **Structure**: 5 scripts (`discover_standards.py`, `inject_standards.py`, `index_standards.py`, `shape_spec.py`, `verify_spec.py`), 3 templates, AST pattern reference.
- **Use when**: Unfamiliar codebase onboarding, shaping feature specs, enforcing deterministic verification before completion.

#### `gemini-context-engineer`
- **Capabilities**: JIT Context Compiler (MIP token bounding ≤600 tokens), VCS AST Delta Daemon (sub-100ms pre-commit sync), Executable Workstream Proofs (anti-premature completion harness)
- **Structure**: 8 scripts, 9 reference guides, 5 test files, evals, benchmarks, assets
- **Use when**: Creating/maintaining GEMINI.md, mapping repo architecture, compiling task context, guarding git boundaries, verifying execution contracts

#### `repo-blast-radius-sync`
- **Capabilities**: Blast radius detection (callers, tests, docs), registry verification, live dashboard (port 8765), orphaned commit blocking
- **Structure**: 5 scripts (`blast_radius.py`, `build_registry.py`, `dashboard.py`, `draft_doc_updates.py`, `verify_parity.py`), 3 references
- **Use when**: Refactoring, adding features, fixing bugs where dependent artifacts must stay in sync

#### `release-sync`
- **Capabilities**: Version parity gate (80/20: FAIL on drift, WARN on hygiene), atomic semver bump across 5 files with rollback, portable (copy-paste to any project)
- **Structure**: 2 scripts (`check.py`, `bump.py`), 2 references (API, examples)
- **Use when**: VERSION/GEMINI.md/package.json drift, CHANGELOG/README hygiene, before semver bump

---

## 🚀 Install

### From Source (Always Works — Recommended)

```bash
git clone https://github.com/Snoozer10/synthesize-skills
cd synthesize-skills
python scripts/validate.py && python scripts/manifest.py
install.ps1 -Force    # Windows
bash install.sh --force  # POSIX
```

**What happens:**
1. Validates all 3 skills (CI gate)
2. Generates `manifest.json` mapping skills → host paths
3. Copies skills to 4 host directories:
   - `.agents/skills/` (canonical)
   - `.claude/skills/`
   - `.opencode/skills/`
   - `.gemini/skills/`
4. SHA256 comparison skips identical files; creates `.bak` backups

### From npm (Published Package)

```bash
# Dual registry: npmjs.org (primary) + GitHub Packages (mirror)
npx --package @snoozer10/synthesize-skills repo-sync add <skill>

# Or install globally
npm i -g @snoozer10/synthesize-skills
repo-sync add <skill>

# Explicitly from GitHub Packages
npm i -g @snoozer10/synthesize-skills --registry=https://npm.pkg.github.com
repo-sync add <skill>
```

**Provenance:** All publishes include SLSA Level 1 provenance attestations via OIDC trusted publishers.

---

## 🖥️ Universal Platform Support (8 Host Ecosystems)

| Platform | Project Target | User-Global Target | Native Adapter |
|---|---|---|---|
| Open Agents Standard | `.agents/skills/` | `~/.agents/skills/` | Canonical SSOT |
| Antigravity / Gemini | `.gemini/skills/` | `~/.gemini/skills/` | `.gemini/rules/*.md` |
| Claude Code / CLI | `.claude/skills/` | `~/.claude/skills/` | `.claude/commands/*.md` |
| OpenAI Codex | `.codex/skills/` | `~/.codex/skills/` | `.codex/instructions/*.md` |
| OpenCode | `.opencode/skills/` | `~/.config/opencode/skills/` | `.opencode/commands/*.md` |
| Cursor | `.cursor/skills/` | `~/.cursor/skills/` | `.cursor/rules/*.mdc` |
| Codeium Windsurf | `.windsurf/skills/` | `~/.codeium/windsurf/skills/` | `.windsurf/rules/*.md` |
| GitHub Copilot | `.copilot/skills/` | `~/.copilot/skills/` | Instructions block |

### Installer CLI Switches
```powershell
# PowerShell (Windows)
.\install.ps1 -Force                                      # Apply auto-detected install
.\install.ps1 -Scope Global -Force                        # Install globally into user profiles (~/.gemini, ~/.claude, etc.)
.\install.ps1 -Target "claude,antigravity" -Force         # Selective multi-host targeting
.\install.ps1 -Rollback                                   # Safely rollback via transaction receipt
```

```bash
# POSIX Shell (Linux / macOS / WSL)
./install.sh --force                                      # Apply auto-detected install
./install.sh --scope global --force                       # Install globally
./install.sh --target "claude,antigravity" --force        # Selective multi-host targeting
./install.sh --rollback                                   # Safely rollback via transaction receipt
```

---

## 🔄 Workflow: RED → GREEN → REFACTOR

Per `docs/WORKFLOW.md`:

1. **RED**: Write 1-3 pressure scenarios in `tests/`, run without skill, record exact failure verbatim
2. **GREEN**: Write smallest `SKILL.md` that fixes baseline failure. Re-run scenarios. Pass = agent complies.
3. **REFACTOR**: Add explicit counters and red-flags for new rationalizations. Re-verify. Keep token cost flat (move heavy refs to `references/`).

**Stop-gate rules:**
- One skill at a time — untested edit = revert
- Never batch-create skills
- Pressure test must exist before skill implementation
- Run `python scripts/validate.py` before every commit

---

## 🛠️ Development Commands

```bash
# Validation (CI gate — REQUIRED before commit)
python scripts/validate.py                    # All skills
python scripts/validate.py .agents/skills/<name>  # Single skill

# Manifest (run after adding/removing skill)
python scripts/manifest.py                    # Generates manifest.json

# Drift gate (dogfooding this repo)
python scripts/release_sync.py --check        # Exit 0 = no drift

# Atomic semver bump (updates 5 files with rollback)
python scripts/release_sync.py --bump patch --apply  # patch|minor|major

# Install
install.ps1                       # Windows dry-run
install.ps1 -Force                # Windows apply
bash install.sh                   # POSIX dry-run
bash install.sh --force           # POSIX apply

# Pre-commit hook (optional)
python scripts/release_sync.py --install-hooks

# Pressure tests
python tests/test_release_sync_pressure.py -v   # Drift detection + atomic bump scenarios
```

---

## 📦 Release Automation

### Standard Release Flow (Triggers OIDC Dual-Registry Publish)

```bash
# 1. Ensure clean working tree and all tests pass
python scripts/validate.py && python scripts/release_sync.py --check

# 2. Bump version (updates VERSION, GEMINI.md, package.json, README region, CHANGELOG)
python scripts/release_sync.py --bump patch --apply  # or minor/major

# 3. Commit version bump
git add VERSION GEMINI.md package.json README.md CHANGELOG.md
git commit -m "chore: release v1.0.2"

# 4. Tag and push (triggers GitHub Actions release.yml)
git tag v1.0.2
git push origin main --tags
```

**What happens on tag push:**
1. `validate` job runs `python scripts/validate.py`
2. `publish-npm` job publishes to npmjs.org with provenance (uses `NPM_TOKEN` secret)
3. `publish-github` job publishes to GitHub Packages with provenance (uses `GITHUB_TOKEN` with `packages: write`)

### Secrets Required

| Secret | Type | How to Create |
|--------|------|---------------|
| `NPM_TOKEN` | **npm automation token** (NOT personal token — 2FA causes EOTP) | `npm token create --type=automation --read-only=false --cidr=0.0.0.0/0` |
| `GITHUB_TOKEN` | Auto-provided by GitHub Actions | Requires `packages: write` permission (set in workflow) |

---

## 🏗️ Architecture

```
synthesize-skills/
├── .agents/skills/           # canonical skills (SSOT)
│   ├── gemini-context-engineer/
│   ├── repo-blast-radius-sync/
│   └── release-sync/
├── templates/
│   └── skill-template/       # SKILL.md starter (not installed)
├── scripts/
│   ├── validate.py           # Skill validator (CI gate)
│   ├── manifest.py           # Generates manifest.json
│   └── release_sync.py       # Version parity gate + atomic bump
├── tests/
│   ├── test_blast_radius_parity.py
│   ├── test_release_sync_pressure.py
│   └── test_release_sync_smoke.py
├── exercises/                # RED-GREEN-REFACTOR learning modules
│   ├── 01-skill-authoring/       # 3 scenarios
│   ├── 02-pressure-testing/      # 2 scenarios
│   ├── 03-validation/            # 2 scenarios
│   └── 04-release-sync/          # 2 scenarios (drift, atomic bump)
├── docs/
│   ├── WORKFLOW.md           # RED-GREEN-REFACTOR stop-gate
│   ├── CONTRIBUTING.md       # Naming, description, validation rules
│   ├── error-solving/
│   │   └── understood-errors.md  # 15+ known error patterns
│   ├── handoff.md            # Session handoff template
│   └── plan/                 # Implementation plans
├── .github/workflows/
│   ├── validate.yml          # CI: validate on push/PR (Windows + Ubuntu)
│   └── release.yml           # CD: OIDC dual-registry publish on v* tags
├── Research and docs/        # upstream research (READ-ONLY)
├── The Created Skills/       # staging area (READ-ONLY)
├── install.ps1               # Windows installer (SHA256 + .bak)
├── install.sh                # POSIX installer (SHA256 + .bak)
├── manifest.json             # skill → host path mapping (generated)
├── VERSION                   # Semver (synced by release_sync.py)
├── GEMINI.md                 # Project context for Gemini CLI
├── CONTINUITY.md             # Project state ledger
├── CHANGELOG.md              # Keep a Changelog format
├── README.md                 # This file
├── package.json              # npm package config
└── LICENSE                   # MIT
```

### Component Reference

| Component | Path | Role |
| :--- | :--- | :--- |
| Canonical Skills | `.agents/skills/` | Single source of truth for all installed skills |
| Starter Template | `templates/skill-template/SKILL.md` | Skeleton for new skills (frontmatter + body) |
| Validator | `scripts/validate.py` | Enforces naming, frontmatter, body structure per skill |
| Manifest Generator | `scripts/manifest.py` | Maps skill → host install paths (`.agents`, `.claude`, `.opencode`, `.gemini`) |
| Release Sync | `scripts/release_sync.py` | Version parity gate + atomic semver bump |
| Pressure Tests | `tests/` | Scenario fixtures verifying skill behavior under edge cases |
| Exercises | `exercises/` | Learning modules: skill-authoring, pressure-testing, validation, release-sync |
| Workflow Guide | `docs/WORKFLOW.md` | RED-GREEN-REFACTOR gate with stop-gate rules |
| Contributing Guide | `docs/CONTRIBUTING.md` | Naming, description, and validation rules |
| Error Catalog | `docs/error-solving/understood-errors.md` | Known error patterns and resolutions |
| Handoff Template | `docs/handoff.md` | Session handoff template for agent continuity |
| CI Pipeline | `.github/workflows/validate.yml` | Runs `scripts/validate.py` on push/PR (Windows + Ubuntu) |
| Release Pipeline | `.github/workflows/release.yml` | OIDC trusted publisher dual-registry publish on `v*` tags |
| Windows Installer | `install.ps1` | Copies skills to host dirs with SHA256 compare and backup |
| POSIX Installer | `install.sh` | Same as above for POSIX systems |

---

## ⚙️ Validation Rules (Exit Codes Matter)

| Check | Severity | Exit Code |
|-------|----------|-----------|
| `name` regex `^[a-z0-9]+(-[a-z0-9]+)*$` | ERROR | 1 |
| `dir == frontmatter name` (allowlist: `skill-template`/`skill-name`) | ERROR | 1 |
| `description` 1-500 chars | ERROR | 1 |
| Frontmatter raw ≤1024 chars | ERROR | 1 |
| Body <500 lines | ERROR | 1 |
| Runnable code fence required (```python\|bash\|sh\|ps1\|js\|ts) | ERROR | 1 |
| `description` starts with "Use when" | WARN | 0 |
| No first-person in description | WARN | 0 |
| No workflow/step-by-step in body | WARN | 0 |
| `Keywords:` required in body | WARN | 0 |
| No `@skills/@name/` links | WARN | 0 |

**Run `python scripts/validate.py` before EVERY commit.** CI runs this on Windows + Ubuntu (Python 3.11).

---

## 🔄 Version Sync (Atomic, 5 Files)

`release_sync.py --bump patch --apply` updates atomically with rollback:

1. `VERSION`
2. `GEMINI.md` (`version:` + `last_indexed:`)
3. `package.json` (`version`)
4. `README.md` (`<!-- release-sync:start -->Version: X.Y.Z<!-- release-sync:end -->`)
5. `CHANGELOG.md` (ensures `## [Unreleased]` exists)

**Never manually edit these version fields.** Use the script.

---

## 🛑 Hard Constraints (Violations = Revert)

1. **Stdlib-only scripts** — `scripts/` uses Python stdlib only. No `pip`/`npm` deps.
2. **One skill at a time** — RED-GREEN-REFACTOR stop-gate (`docs/WORKFLOW.md`). Untested edit = revert.
3. **No batch-create** — Pressure test first (RED), minimal skill second (GREEN), close loopholes third (REFACTOR).
4. **Read-only zones** — Never touch `Research and docs/` or `The Created Skills/` without explicit ask.
5. **Dir name = frontmatter `name`** — Only `skill-template`/`skill-name` allowlisted mismatch.
6. **Validate before commit** — `python scripts/validate.py` must exit 0.

---

## 🧪 Testing Quirks

- **No pytest/Jest** — Validation IS the test suite. `scripts/validate.py` is the gate.
- **Pressure tests** live in `tests/` (e.g., `test_release_sync_pressure.py` for drift/bump scenarios).
- **Exercises** in `exercises/` are learning modules, not CI tests.
- **Pre-commit hook** available: `python scripts/release_sync.py --install-hooks`

---

## 🔧 OpenCode Config (`.opencode.json`)

```json
{
  "default_agent": "orchestrator",
  "subagent_depth": 3,
  "agent": {
    "orchestrator": {
      "model": "opencode/nemotron-3-ultra-free",
      "permission": { "read": "allow", "glob": "allow", "grep": "allow", "list": "allow", "edit": "deny", "write": "deny", "bash": "deny" }
    }
  },
  "provider": { "opencode": { "options": { "blacklist": ["opencode/big-pickle", "opencode/muse-spark-1.2-free"] } } }
}
```

**Orchestrator is read-only conductor.** Subagents: `@plan`, `@explorer`, `@private-builder`, `@sandboxed-builder`, `@architect`, `@auditor`.

---

## 📁 Key Files to Know

| File | Purpose |
|------|---------|
| `scripts/validate.py` | Skill validator (CI gate) |
| `scripts/release_sync.py` | Version parity gate + atomic bump |
| `scripts/manifest.py` | Generates `manifest.json` |
| `.github/workflows/validate.yml` | CI: validate on push/PR (Windows + Ubuntu) |
| `.github/workflows/release.yml` | CD: OIDC dual-registry publish on `v*` tags |
| `docs/WORKFLOW.md` | RED-GREEN-REFACTOR stop-gate rules |
| `docs/CONTRIBUTING.md` | Naming, description, validation rules |
| `docs/error-solving/understood-errors.md` | Known error patterns & resolutions |
| `docs/handoff.md` | Session handoff template |
| `CONTINUITY.md` | Project state ledger (updated per task) |
| `GEMINI.md` | Project context for Gemini CLI |
| `CHANGELOG.md` | Keep a Changelog format |

---

## ⚠️ Common Pitfalls (Agents Miss These)

| Pitfall | Fix |
|---------|-----|
| Editing `Research and docs/` or `The Created Skills/` | Don't. Read-only unless explicitly asked. |
| Forgetting `python scripts/manifest.py` after adding skill | Run it. `manifest.json` must be committed. |
| Using personal npm token (2FA) in CI | Use **automation token**: `npm token create --type=automation` |
| Missing `packages: write` for GitHub Packages | Workflow has `permissions: packages: write` at job level. |
| Manually editing VERSION/package.json/GEMINI.md | Use `release_sync.py --bump patch --apply` |
| Batch-creating skills | One at a time. RED → GREEN → REFACTOR. |
| Assuming `validate.py` catches everything | Run it against the specific skill: `python scripts/validate.py .agents/skills/<name>` |

---

## 🔗 References

- Workflow: `docs/WORKFLOW.md`
- Contributing: `docs/CONTRIBUTING.md`
- Error Solving: `docs/error-solving/understood-errors.md`
- Handoff Template: `docs/handoff.md`
- Changelog: `CHANGELOG.md`
- Continuity Ledger: `CONTINUITY.md`
- License: `LICENSE`

<!-- release-sync:start -->
Version: 1.0.1
<!-- release-sync:end -->