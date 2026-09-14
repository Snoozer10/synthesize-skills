# Handoff Template — synthesize-skills

> **Purpose:** Standardized session handoff for agent continuity. Fill all sections before ending session.

---

## 📋 Session Metadata

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Session ID** | (auto-generated or manual) |
| **Branch** | `main` |
| **HEAD Commit** | `git rev-parse --short HEAD` |
| **Version** | `cat VERSION` |
| **Agent** | (orchestrator / @private-builder / @plan / etc.) |

---

## ✅ Completed This Session

| Task | Status | Verification |
|------|--------|--------------|
| | | |
| | | |
| | | |

---

## 🔄 In Progress (Handoff Required)

| Task | Current State | Blockers | Next Steps |
|------|---------------|----------|------------|
| | | | |
| | | | |

---

## ⏭️ Next Priority Tasks

1. **Immediate:** 
2. **Short-term:** 
3. **Backlog:** 

---

## 🧠 Critical Context for Next Agent

### Key Decisions Made
- 
- 

### Files Modified (Uncommitted)
- 
- 

### Environment State
- Git status: `git status --porcelain`
- Validation: `python scripts/validate.py` → (pass/fail)
- Drift check: `python scripts/release_sync.py --check` → (pass/fail)

### Gotchas / Traps
- 
- 

---

## 🔐 Secrets & Auth Status

| Service | Status | Notes |
|---------|--------|-------|
| GitHub CLI (`gh auth status`) | | Scopes: |
| npm token (`NPM_TOKEN` secret) | | Configured in GitHub Actions |
| GitHub Packages (`GITHUB_TOKEN`) | | OIDC via `id-token: write` |

---

## 📁 Workspace Snapshot

```
synthesize-skills/
├── .agents/skills/           # Skills count: 
├── docs/
│   └── error-solving/        # understood-errors.md: 
├── exercises/
│   └── 04-release-sync/      # Exercises: 
├── GEMINI.md                 # version: , last_indexed: 
├── CONTINUITY.md             # Updated: 
├── README.md                 # 
├── CHANGELOG.md              # [Unreleased] entries: 
├── VERSION                   # 
└── package.json              # version: 
```

---

## 🚀 Quick Resume Commands

```bash
# Restore context
cat CONTINUITY.md
cat GEMINI.md

# Verify baseline
python scripts/validate.py
python scripts/release_sync.py --check
git status

# Resume work
# (continue from "Next Priority Tasks" above)
```

---

## 📝 Notes for Next Session

> Free-form notes, observations, or context that doesn't fit above.

---

*Template version: 1.0 | Project: synthesize-skills | Update CONTINUITY.md after each session*