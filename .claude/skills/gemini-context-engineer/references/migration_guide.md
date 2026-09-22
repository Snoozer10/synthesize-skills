# Migration & Smart Merge Protocol

This guide outlines the deterministic procedure for migrating legacy context files (unstructured `GEMINI.md`, `CLAUDE.md`, `.cursorrules`, or monolithic developer READMEs) into the strict 5-tier anatomy enforced by `gemini-context-engineer`.

---

## 1. The Non-Destructive Backup Routine

Before modifying or replacing any existing context file, create a non-destructive rotating backup.

### Backup Specifications:
1. **Timestamp Pattern**: `GEMINI.md.<YYYYMMDD_HHMMSS>.bak`
   - Example: `GEMINI.md.20260903_043000.bak`
2. **Pruning Policy**:
   - Inspect existing `.bak` files matching the pattern.
   - Retain the most recent 3 backups.
   - Automatically delete older backup files to prevent workspace pollution.

```python
# Conceptual reference for rotating backup
import os, glob
from datetime import datetime

def create_rotating_backup(target_path="GEMINI.md", max_backups=3):
    if not os.path.exists(target_path):
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{target_path}.{timestamp}.bak"
    with open(target_path, "rb") as src, open(backup_name, "wb") as dst:
        dst.write(src.read())
    
    # Prune older backups
    backups = sorted(glob.glob(f"{target_path}.*.bak"))
    if len(backups) > max_backups:
        for old_file in backups[:-max_backups]:
            os.remove(old_file)
    return backup_name
```

---

## 2. Four-Phase Smart Merge Protocol

Follow these four sequential phases when refactoring an existing project context:

```text
┌────────────────────────────┐
│ Phase 1: Ingestion & Parse │ -> Read existing context & run repo_indexer.py
└─────────────┬──────────────┘
              │
┌─────────────▼──────────────┐
│ Phase 2: Invariant Harvest │ -> Extract tribal rules & bespoke negative bounds
└─────────────┬──────────────┘
              │
┌─────────────▼──────────────┐
│ Phase 3: Five-Tier Assembly│ -> Map extracted data into golden structure
└─────────────┬──────────────┘
              │
┌─────────────▼──────────────┐
│ Phase 4: Validation Gate   │ -> Run validate_gemini_md.py --json --strict
└────────────────────────────┘
```

### Phase 1: Ingestion & Ground-Truth Indexing
1. Read the legacy context file completely into memory.
2. Run `python <SKILL_DIR>/scripts/repo_indexer.py --root . --json` to obtain the verified ground truth:
   - Real dependency versions.
   - Real file tree and existing directories.
   - Real script invocations configured in project manifests.

### Phase 2: Invariant Harvesting
Identify and protect custom engineering rules that cannot be re-discovered by scripts:
- **Bespoke Business Logic**: Domain constraints (e.g., "All monetary calculations must use integer cents").
- **Hardware / OS Invariants**: Hardware constraints (e.g., "Intel QSV lookahead must be set to 0", "Audacity IPC requires Windows Named Pipes").
- **Negative Boundaries**: Rules explicitly stating what NOT to do (e.g., "NEVER mock the database in integration tests", "DO NOT import server components in client files").
- **Tribal Knowledge**: Non-standard environment configurations or undocumented flags.

> [!CRITICAL]
> **Preservation Guarantee**: Never discard domain-specific negative constraints during migration. If in doubt, preserve the rule inside `## 🛑 Mandatory Engineering Constraints`.

### Phase 3: Five-Tier Assembly

Distribute legacy content into the target sections using this routing matrix:

| Legacy Content Type | Target Destination | Transformation Action |
| :--- | :--- | :--- |
| Project summary, mission, target audience | `## 🎯 Project Overview` | Condense to 1-2 high-density paragraphs. Strip marketing fluff. |
| Folder lists, file explanations, architecture diagrams | `## 🏗️ Architecture & Component Mapping` | Convert to structured table (`Component \| Path \| Responsibility`) or ASCII tree (depth $\le 2$). |
| Code style, tabs/spaces, quote rules | **DISCARD** | Purge via Inferable Rule (delegate to linters/formatters). |
| Non-negotiable architectural rules, negative bounds | `## 🛑 Mandatory Engineering Constraints` | Group into numbered bullets or thematic subsections. |
| Rule summaries / tags | Frontmatter `rules:` | Convert key invariants into machine-readable kebab-case slugs. |
| Build, test, lint, dev scripts | `## 🛠️ Common Workflows & CLI Commands` | Verify against actual manifests. Keep only verified commands with flags. |
| In-progress branch work, failing tests, blockers | `## 🔄 Active Workstreams & Verification Status` | Format as 5-column DAG table with mandatory `Proof Command`. |
| Long-term vision, Q3/Q4 plans, wishlist features | Move to `ROADMAP.md` | Exclude from `GEMINI.md` to prevent volatility drift. |

### Section 5 (Active Workstreams) Migration: Mandatory `Proof Command`

When upgrading legacy context files from v1/v2/v3 to Version 4.0.0 Enterprise, Section 5 (`## 🔄 Active Workstreams & Verification Status`) transitions from passive text or 4-column tables into an **executable verification contract** enforced by `verify_proofs.py`.

#### Mandatory 5-Column Schema:
Every row in the Section 5 DAG table must include the fifth column: `Proof Command`.

```markdown
| ID | Workstream Slice | Status | Blocked By | Proof Command |
| :--- | :--- | :--- | :--- | :--- |
| `#1` | Core Domain & State Model Slice | Done | - | `pytest tests/unit/test_domain.py -v` |
| `#2` | Ingestion Pipeline & Serialization | In Progress | `#1` | `pytest tests/unit/test_pipeline.py -v` |
| `#3` | Static Typing & Linting Gate | Pending | `#2` | `ruff check src/ && mypy src/ --strict` |
```

#### Concrete Proof Command Migration Examples:
1. **Unit & Integration Tests (`pytest`)**:
   - *Legacy*: `"Unit tests pass"` (narrative assertion)
   - *v4.0.0 Migration*: `pytest tests/unit/test_auth.py -v` or `python -m pytest tests/unit`
2. **Linter & Code Quality Gates (`ruff check`)**:
   - *Legacy*: `"Code cleaned and formatted"`
   - *v4.0.0 Migration*: `ruff check src/ --fix && ruff format --check src/`
3. **Static Typecheck Gates (`mypy`)**:
   - *Legacy*: `"Types verified"`
   - *v4.0.0 Migration*: `mypy src/ --strict --no-error-summary`
4. **Compound Verification Pipeline**:
   - *v4.0.0 Migration*: `ruff check src/ && mypy src/ --strict && pytest tests/unit/ -v`

#### Migration Invariants:
- **Zero Self-Reported Done**: Never mark a task `Done` without an executable proof command.
- **Topological Acyclicity**: Ensure `Blocked By` references form an acyclic directed graph verified by `graphlib.TopologicalSorter`.
- **Non-Interactive Execution**: Proof commands must execute without user interaction and exit with code `0`.

### Phase 4: Validation Gate
1. Save the newly structured `GEMINI.md`.
2. Run `python <SKILL_DIR>/scripts/validate_gemini_md.py GEMINI.md --json --strict`.
3. If the validator reports errors, apply the self-correction remediation protocols outlined in `SKILL.md`.

---

## 3. Post-Migration Verification Checklist

Before considering the migration complete, confirm:
- [ ] Rotating backup was generated (`GEMINI.md.<timestamp>.bak`).
- [ ] Single H1 header matches `# Project Context: <name>`.
- [ ] Exactly 5 H2 headers exist with the correct emojis (`🎯`, `🏗️`, `🛑`, `🛠️`, `🔄`).
- [ ] Total line count is $\le 350$ lines.
- [ ] All relative and `file:///` links point to existing files.
- [ ] Frontmatter contains all 7 mandatory keys.
- [ ] Zero linter/formatting rules remain in Section 3.
- [ ] Section 5 workstream table includes mandatory `Proof Command` column with deterministic test commands.
- [ ] `validate_gemini_md.py --strict` exits with code `0`.
- [ ] `verify_proofs.py --file GEMINI.md --check-only` validates all workstream contracts.
