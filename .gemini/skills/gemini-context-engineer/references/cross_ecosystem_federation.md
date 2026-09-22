# Cross-Ecosystem Context Federation Guide

This guide details the single-source-of-truth (SSOT) architecture for synchronizing context files across divergent AI coding agent ecosystems: Google Gemini / Antigravity CLI, Anthropic Claude Code, OpenCode / DOX, and Cursor IDE.

---

## 1. The Split-Brain Context Problem

Modern engineering teams frequently deploy multi-agent toolchains across different ecosystems. Each agent runtime hardcodes an expected context filename:

| Agent Runtime / Tool | Expected Context Filename | Primary Parsing Behavior |
| :--- | :--- | :--- |
| **Gemini CLI / Antigravity CLI** | `GEMINI.md` | Authoritative 5-tier context with schema & budget validation |
| **Claude Code** | `CLAUDE.md` | Ingested into Claude context at startup |
| **OpenCode / Aider** | `AGENTS.md` | Evaluated along directory tree for local operating contracts |
| **Cursor IDE** | `.cursorrules` | Project rules injected into AI prompt window |

When these files exist simultaneously as unlinked, separate documents, repositories suffer from **Split-Brain Drift**:
- An engineer or agent updates test commands in `CLAUDE.md`.
- Another agent reads outdated commands from `GEMINI.md`.
- Contradictory rules accumulate, leading to broken builds, hallucinated APIs, and inconsistent code styles.

---

## 2. The Single Source of Truth (SSOT) Architecture

`gemini-context-engineer` establishes `GEMINI.md` as the canonical, validated Single Source of Truth. All satellite context files (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`) are federated directly to `GEMINI.md`.

```text
                        ┌──────────────────────────────┐
                        │   Authoritative SSOT         │
                        │        GEMINI.md             │
                        │  (5-Tier, Strict Budget)     │
                        └──────────────┬───────────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            ▼                          ▼                          ▼
┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│       CLAUDE.md       │  │       AGENTS.md       │  │     .cursorrules      │
│ (Symlink/Pointer Shim)│  │ (Symlink/Pointer Shim)│  │ (Symlink/Pointer Shim)│
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
```

---

## 3. Synchronization Mechanisms: Symlinks vs. Pointer Shims

Federation operates via two distinct mechanisms depending on filesystem privileges and host OS:

### Mechanism A: Symbolic Links (Preferred on POSIX & Windows Dev Mode)
When supported by the host OS and user privileges, satellite context files are created as relative symbolic links targeting `GEMINI.md`:
```bash
ln -s GEMINI.md CLAUDE.md
ln -s GEMINI.md AGENTS.md
ln -s GEMINI.md .cursorrules
```
- **Pros**: Zero maintenance overhead; zero token redundancy; bi-directional live updates.
- **Cons**: Requires elevated privileges or Developer Mode on Windows (`SeCreateSymbolicLinkPrivilege`).

### Mechanism B: Standardized Pointer Shims (Cross-Platform Resilient)
When symlink creation fails (or on systems with strict symlink restrictions), `gemini-context-engineer` writes a standardized **Pointer Shim**:

```markdown
<!-- AGENT-SYNC: GEMINI.md -->
# Synced Context
This repository uses [GEMINI.md](./GEMINI.md) as the authoritative context file. Please refer to GEMINI.md for all project instructions, architecture, and constraints.
```

- **Magic Token**: The `<!-- AGENT-SYNC: GEMINI.md -->` comment allows automated tooling to identify the file as an active pointer shim rather than divergent content.
- **Agent Behavior**: Claude Code, OpenCode, and Cursor AI models immediately follow the relative markdown link to `./GEMINI.md`.

---

## 4. Automated Federation Workflows

### 1. Ingest & Federate via CLI
Execute repository indexing with the `--federate` flag:
```powershell
python <SKILL_DIR>/scripts/repo_indexer.py --root . --federate --json
```
This performs the following deterministic sequence:
1. Scans root for `CLAUDE.md`, `AGENTS.md`, and `.cursorrules`.
2. Inspects content for divergence.
3. If missing or divergent, attempts relative symlink creation to `GEMINI.md`.
4. If symlink creation fails with `OSError`, automatically writes the standardized pointer shim.

### 2. Validation & Split-Brain Warning
`validate_gemini_md.py` continuously monitors satellite files:
```powershell
python <SKILL_DIR>/scripts/validate_gemini_md.py GEMINI.md --strict
```
- If a satellite file exists and contains independent, non-shimmed content, the validator flags:
  `WARN_SPLIT_BRAIN_CONTEXT: 'CLAUDE.md' exists and diverges from GEMINI.md. Run with --federate to align.`
- In `--strict` mode, this warning blocks CI/CD pipelines until federation is restored.

---

## 5. Migration Checklist for Legacy Repositories

When adopting `gemini-context-engineer` on a repository with existing `CLAUDE.md` or `.cursorrules`:

1. **Harvest Invariants**: Extract unique rules, architecture details, and custom commands from the legacy file into `GEMINI.md` (Sections 2, 3, and 4).
2. **Backup Legacy Files**: Preserve originals via `.bak` if necessary.
3. **Execute Federation**: Run `repo_indexer.py --federate`.
4. **Validate Alignment**: Run `validate_gemini_md.py GEMINI.md --strict` to verify zero split-brain warnings.
