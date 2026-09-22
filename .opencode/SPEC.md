# SPECIFICATION: Documentation Audit & Updates + Version Bump

## 1. Executive Summary & Scope
- **Objective:** Audit and update all project documentation, create missing continuity/handoff files, expand exercises, and bump version to 1.0.1
- **In-Scope Deliverables:**
  1. Create `docs/error-solving/understood-errors.md` with known error patterns
  2. Expand `exercises/` with new pressure scenarios for release-sync skill
  3. Update `GEMINI.md` — `last_indexed`, new learnings, version sync
  4. Create `CONTINUITY.md` — project state ledger
  5. Create `docs/handoff.md` — session handoff template
  6. Update `README.md` — GitHub Packages badge, dual registry install
  7. Update `CHANGELOG.md` — [Unreleased] entries for OIDC release workflow
  8. Bump `VERSION` to 1.0.1 (patch) + sync `package.json` + `GEMINI.md` + `README.md` region
- **Out-of-Scope:**
  - Modifying `Research and docs/` or `The Created Skills/` (read-only)
  - Changing skill validation rules

## 2. Codebase Impact & File Map
- **Files to Create:**
  - `docs/error-solving/understood-errors.md`
  - `CONTINUITY.md`
  - `docs/handoff.md`
  - New exercise scenarios in `exercises/`
- **Files to Modify:**
  - `GEMINI.md` — version, last_indexed, learnings, workstreams
  - `README.md` — badges, install methods
  - `CHANGELOG.md` — [Unreleased] section
  - `VERSION` — 1.0.0 → 1.0.1
  - `package.json` — version sync
- **Files to Verify:**
  - `scripts/release_sync.py --check` passes after all changes

## 3. Atomic Implementation Steps

### Step 1: Create docs/error-solving/understood-errors.md
- **Target:** New file documenting known error patterns and solutions
- **Content:** Error patterns from development (npm auth, tag force-push, OIDC config, etc.)
- **Format:** Markdown with error → cause → solution structure

### Step 2: Expand exercises/ with release-sync pressure scenarios
- **Target:** Add new exercise module for release-sync skill
- **Content:** 
  - `exercises/04-release-sync/04.01-drift-detection/` — drift gate failure scenarios
  - `exercises/04-release-sync/04.02-atomic-bump/` — version bump atomicity
- **Structure:** Each with `problem/`, `solution/`, `explainer/` subdirs

### Step 3: Update GEMINI.md
- **Target:** Sync version, last_indexed, add learnings
- **Changes:**
  - `version: "1.0.1"`
  - `last_indexed: "2026-09-14"`
  - Add LEARNING-002: OIDC trusted publisher setup
  - Add LEARNING-003: GitHub Packages Actions access vs npm Trusted Publisher
  - Update workstreams table with completed OIDC workflow

### Step 4: Create CONTINUITY.md
- **Target:** Project state ledger per continuity protocol
- **Content:** 
  - Done: npmjs.org publish, GitHub Packages publish, OIDC workflow, tag update
  - Now: Documentation audit, version bump
  - Next: Next skill development cycle

### Step 5: Create docs/handoff.md
- **Target:** Session handoff template
- **Content:** Standardized handoff format for agent sessions

### Step 6: Update README.md
- **Target:** Add GitHub Packages badge, dual registry install instructions
- **Changes:**
  - Add GitHub Packages version badge
  - Update install section with dual registry info
  - Add provenance note

### Step 7: Update CHANGELOG.md
- **Target:** Add [Unreleased] entries
- **Content:** OIDC release workflow, GitHub Packages publish, tag force-update

### Step 8: Version Bump (1.0.0 → 1.0.1)
- **Target:** Atomic bump via `scripts/release_sync.py --bump patch --apply`
- **Sync:** VERSION, package.json, GEMINI.md, README.md region, CHANGELOG.md

## 4. Execution Routing & Security Gate
- **Assigned Builder:** `@private-builder` (MiMo V2.5) — handles all file writes
- **Planning:** `@plan` (Nemotron 3 Ultra) — already done in this SPEC
- **Verification Commands:**
  - `python scripts/validate.py` — all skills pass
  - `python scripts/release_sync.py --check` — drift gate clean
  - `python scripts/manifest.py` — manifest regenerated
- **Auditor Checklist:**
  - [ ] All new files created with correct structure
  - [ ] GEMINI.md version/last_indexed synced
  - [ ] README.md badges and install methods updated
  - [ ] CHANGELOG.md has [Unreleased] entries
  - [ ] VERSION = package.json = GEMINI.md = 1.0.1
  - [ ] release_sync --check passes (exit 0)
  - [ ] validate.py passes (exit 0)
  - [ ] No read-only zones modified

## 5. Dependencies & Prerequisites
- All Phase 1 changes must pass validation before Phase 2 (release test)
- Version bump must be atomic (release_sync.py --bump patch --apply)

---

### 📋 Specification Complete
The detailed architectural plan has been written to `.opencode/SPEC.md`.

**Next Step to Build:**
Press **`Tab`** → **BUILD MODE** → instruct:
> *"Execute the approved plan in `.opencode/SPEC.md` using `@private-builder`, then have `@auditor` verify the staged diff."*