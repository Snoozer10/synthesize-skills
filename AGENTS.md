# AGENTS.md — synthesize-skills

> Compact instruction file for OpenCode sessions. Every line answers: "Would an agent likely miss this without help?"

---

## 🎯 Repo Purpose
Workspace for authoring, validating, and installing reusable AI-agent skills. Skills are `SKILL.md` files with YAML frontmatter, validated by `scripts/validate.py`, installed across 8 host targets (`.agents/skills`, `.claude/skills`, `.opencode/skills`, `.gemini/skills`, `.codex/skills`, `.cursor/skills`, `.windsurf/skills`, `.copilot/skills`).

---

## 🔑 Critical Commands (Exact, Non-Obvious)

```bash
# Validate ALL skills (CI gate — REQUIRED before commit)
python scripts/validate.py

# Validate SINGLE skill
python scripts/validate.py .agents/skills/<name>

# Generate manifest.json (maps skill → 8 host install paths)
python scripts/manifest.py

# Compile native adapters (Claude commands, Cursor rules, Gemini rules, OpenCode, Codex, Windsurf)
python scripts/compile_adapters.py

# Dry-run install (shows what would be copied)
install.ps1                    # Windows
bash install.sh                # POSIX

# Apply install (copies across target host dirs)
install.ps1 -Force             # Windows
bash install.sh --force        # POSIX

# Global install to user home profiles
install.ps1 -Scope Global -Force
bash install.sh --scope global --force

# Rollback installation
install.ps1 -Rollback
bash install.sh --rollback

# Drift gate (dogfooding this repo)
python scripts/release_sync.py --check

# Atomic semver bump (updates VERSION, GEMINI.md, package.json, README region, CHANGELOG)
python scripts/release_sync.py --bump patch --apply

# Run pressure tests (release-sync exercises)
python tests/test_release_sync_pressure.py -v
```

---

## 🏗️ Architecture (Non-Obvious Boundaries)

| Path | Role | Notes |
|------|------|-------|
| `.agents/skills/` | **Canonical SSOT** | Only source of truth. Install scripts are consumers. |
| `templates/skill-template/` | Starter only | Not installed. Copy to `.agents/skills/<name>/SKILL.md` for new skills. |
| `Research and docs/` | **READ-ONLY** | Never edit without explicit ask. Still checked by `validate.py` locally. |
| `The Created Skills/` | **READ-ONLY** | Staging area. Never edit without explicit ask. |
| `.agent/` inside a skill | Skill-internal | Not this repo's registry. |

---

## 📋 Validation Rules (Exit Codes Matter)

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

## 🔄 Release Workflow (Dual Registry + OIDC)

**Trigger:** Push tag `v*` (e.g., `git tag v1.1.0 && git push origin v1.1.0`)

**Pipeline (`.github/workflows/release.yml`):**
1. `validate` job → `python scripts/validate.py`
2. `publish-npm` job → `npm publish --provenance --access public` (uses `NPM_TOKEN` secret)
3. `publish-github` job → `npm publish --provenance` (uses `GITHUB_TOKEN` with `packages: write`)

**Secrets Required:**
- `NPM_TOKEN` = **npm Classic Automation token** (NOT personal/publish token — 2FA causes EOTP failure; create on npmjs.com → Access Tokens → Classic Token → Automation scope)
- `GITHUB_TOKEN` = auto-provided, needs `packages: write` permission (set in workflow)

**Provenance:** SLSA Level 1 attestations published to sigstore transparency log.

---

## 📦 Version Sync (Atomic, 5 Files)

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
| `docs/error-solving/understood-errors.md` | Known error patterns & resolutions |
| `CONTINUITY.md` | Project state ledger (updated per task) |
| `GEMINI.md` | Project context for Gemini CLI |

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
- Error Catalog: `docs/error-solving/understood-errors.md`
- Handoff Template: `docs/handoff.md`
- Changelog: `CHANGELOG.md`
- Continuity Ledger: `CONTINUITY.md`