# Cross-Ecosystem Context Federation Guide

This guide details the single-source-of-truth (SSOT) architecture for synchronizing context files across divergent AI coding agent ecosystems: Google Gemini / Antigravity CLI, Anthropic Claude Code, OpenCode / DOX, and Cursor IDE.

---

## 1. The Split-Brain Context Problem & Ecosystem Role Split

Modern engineering teams frequently deploy multi-agent toolchains across different ecosystems. Each agent runtime hardcodes an expected context filename and serves a distinct primary role:

| Agent Runtime / Tool | Expected Context Filename | Ecosystem Role & Responsibility | Primary Parsing Behavior |
| :--- | :--- | :--- | :--- |
| **Google Antigravity 2.0 / CLI / IDE** | `GEMINI.md` | Canonical Single Source of Truth (SSOT) for architecture, engineering constraints, workflows, and standards | Authoritative 5-tier context with schema & budget validation |
| **Claude CLI & Claude Code Desktop** | `CLAUDE.md` | Anthropic Claude ecosystem agent instructions and developer preferences | Ingested into Claude context at startup |
| **OpenCode / Codex / Aider / Other AI Agents** | `AGENTS.md` | OpenCode orchestrator permissions, model configs, tool definitions, multi-agent contracts | Evaluated along directory tree for local operating contracts |
| **Cursor IDE** | `.cursorrules` | Cursor IDE prompt rules, editor behaviors, and file-pattern triggers | Project rules injected into AI prompt window |

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
│(Symlink/Hybrid Shim)  │  │(Symlink/Hybrid Shim)  │  │(Symlink/Hybrid Shim)  │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
```

---

## 3. Synchronization Mechanisms: Symlinks vs. Non-Destructive Hybrid Shims

Federation operates via two distinct mechanisms depending on filesystem privileges, host OS, and whether the satellite context file contains existing user configurations:

### Mechanism A: Symbolic Links (Preferred on POSIX & Windows Dev Mode)
When supported by the host OS and user privileges, satellite context files without independent customization can be created as relative symbolic links targeting `GEMINI.md`:
```bash
ln -s GEMINI.md CLAUDE.md
ln -s GEMINI.md AGENTS.md
ln -s GEMINI.md .cursorrules
```
- **Pros**: Zero maintenance overhead; zero token redundancy; bi-directional live updates.
- **Cons**: Requires elevated privileges or Developer Mode on Windows (`SeCreateSymbolicLinkPrivilege`). Wipes existing customized satellite instructions if overwritten.

### Mechanism B: Non-Destructive Authoritative Directive Injection (Hybrid Shims)
When symlinks are unsupported or when preserving satellite-specific agent configurations (such as OpenCode orchestrator permissions in `AGENTS.md`, custom Claude instructions in `CLAUDE.md`, or editor rules in `.cursorrules`) is necessary, `gemini-context-engineer` injects an idempotent, non-destructive **Authoritative SSOT Directive**:

```markdown
<!-- AGENT-SYNC: GEMINI.md:start -->
<!-- AGENT-SYNC: GEMINI.md -->
> [!IMPORTANT]
> **AUTHORITATIVE CONTEXT DIRECTIVE**:
> Read [GEMINI.md](./GEMINI.md) now and use it as the current project guidance where it differs from <target_filename>.
> `GEMINI.md` is the canonical Single Source of Truth (SSOT) for this repository's architecture, engineering constraints, workflows, and standards.
> All rules, commands, and workstream states defined in `GEMINI.md` supersede any conflicting instructions below.
<!-- AGENT-SYNC: GEMINI.md:end -->
```

#### Federation Classification States:
1. **`missing`**: The file does not exist on disk. When federated, a standardized pointer shim is written with the authoritative banner and a link to `./GEMINI.md`.
2. **`symlink`**: The file is a filesystem symbolic link targeting `GEMINI.md`.
3. **`pointer_shim`**: A lightweight shim containing only the authoritative directive and `# Synced Context` link.
4. **`federated_hybrid`**: The file contains the authoritative directive banner *and* preserves substantive local agent instructions below it (e.g. OpenCode orchestrator permissions, Claude custom behaviors).
5. **`divergent`**: The file has independent content but lacks the authoritative directive banner. Detected by `validate_gemini_md.py` and flagged as `WARN_SPLIT_BRAIN_CONTEXT`.

---

## 4. Automated Federation Workflows

### 1. Ingest & Federate via CLI
Execute repository indexing with the `--federate` flag:
```powershell
python <SKILL_DIR>/scripts/repo_indexer.py --root . --federate --json
```
or via the validator:
```powershell
python <SKILL_DIR>/scripts/validate_gemini_md.py GEMINI.md --federate
```
This performs the following deterministic sequence:
1. Scans root for `CLAUDE.md`, `AGENTS.md`, and `.cursorrules`.
2. Inspects content for divergence via `classify_federation_file`.
3. If missing or divergent, attempts non-destructive authoritative SSOT directive injection:
   - For missing or empty files, creates a pointer shim.
   - For existing files with substantive configurations, prepends or updates the bounded `<!-- AGENT-SYNC: GEMINI.md:start -->` banner non-destructively, preserving all original content.
4. If symlinks are explicitly preferred and supported, creates relative symlinks.

### 2. Validation & Split-Brain Warning
`validate_gemini_md.py` continuously monitors satellite files:
```powershell
python <SKILL_DIR>/scripts/validate_gemini_md.py GEMINI.md --strict
```
- If a satellite file exists and contains independent content lacking the authoritative SSOT directive banner, the validator flags:
  `WARN_SPLIT_BRAIN_CONTEXT: '<filename>' exists and diverges from GEMINI.md. Run with --federate to align.`
- In `--strict` mode, this warning blocks CI/CD pipelines until federation is aligned.
- When the authoritative banner is present, the file is recognized as `federated_hybrid` and emits zero split-brain warnings.

---

## 5. Migration Checklist for Legacy Repositories

When adopting `gemini-context-engineer` on a repository with existing `CLAUDE.md`, `AGENTS.md`, or `.cursorrules`:

1. **Harvest Invariants**: Extract unique rules, architecture details, and custom commands from the legacy file into `GEMINI.md` (Sections 2, 3, and 4).
2. **Preserve Agent Configurations**: Subagent permissions, model routing, and editor-specific triggers remain in their respective satellite files (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`).
3. **Execute Federation**: Run `repo_indexer.py --federate` or `validate_gemini_md.py --federate` to inject the authoritative SSOT directive non-destructively.
4. **Validate Alignment**: Run `validate_gemini_md.py GEMINI.md --strict` to verify zero split-brain warnings.
