# Token Budget Heuristics & Context Hygiene

Context window space is finite, expensive, and subject to cognitive degradation (the "lost-in-the-middle" effect). When a `GEMINI.md` file exceeds density thresholds, autonomous agents experience increased hallucination rates, lose track of constraints, and consume unnecessary latency and inference budget.

This document establishes the official heuristics, subtraction directives, and token budgeting limits enforced by `gemini-context-engineer`.

---

## 1. The "Inferable Rule" Decision Tree

Before adding or retaining any rule, constraint, or instruction in `GEMINI.md`, route it through the **Inferable Rule Framework**:

```text
                           CAN THE CONSTRAINT BE
                    DIRECTLY INFERRED FROM SOURCE CODE?
                                  │
                  ┌───────────────┴───────────────┐
                 YES                              NO
                  │                               │
        Does a tool enforce it?          Does breaking it cause
       (Prettier, ESLint, Ruff,         silent or catastrophic bugs?
        TypeScript, Rustc, MyPy)                  │
          │               │                 ┌─────┴─────┐
         YES              NO               YES          NO
          │               │                 │           │
       DISCARD         DISCARD           PRESERVE    DISCARD
     (Linter job)   (Self-evident)    (Critical Rule) (Trivial noise)
```

### Evaluation Criteria:
1. **Tool-Enforced Rule**: If a static analyzer, compiler, linter, or formatter catches the violation during standard build or CI verification, do not document it in markdown.
2. **Self-Evident Idiom**: If any experienced developer in that programming language writes it naturally (e.g., standard idiomatic loops or error wrapping), do not document it.
3. **Critical Rule**: If violating this constraint causes silent corruption, race conditions, security vulnerabilities, or hard-to-debug runtime failures that automated tools miss, **document it prominently**.

---

## 2. Four Subtraction Directives

Apply these four subtraction directives during initial synthesis, auditing, and refactoring:

### Directive 1: Purge Formatting Rules
- **Purge**: Indentation depth (spaces vs. tabs), maximum line length, single vs. double quotes, trailing commas, bracket spacing, or import sorting order.
- **Rationale**: Linters and auto-formatters (`prettier`, `black`, `ruff format`, `gofmt`, `rustfmt`) handle 100% of formatting deterministically. Stating these rules in markdown wastes tokens and invites agent distraction.

### Directive 2: Purge Idiomatic Language Defaults
- **Purge**: Standard language idioms that baseline models already understand:
  - *Wrong*: "Use list comprehensions instead of map/filter where appropriate in Python."
  - *Wrong*: "Always handle errors in Go using `if err != nil`."
  - *Wrong*: "Use async/await instead of raw Promises in TypeScript."
  - *Wrong*: "Prefer `const` over `let` when variables are not reassigned."
- **Rationale**: Frontier models are pre-trained on billions of lines of idiomatic code. Re-stating textbook idioms dilutes attention from project-specific business logic.

### Directive 3: Purge Raw Dependency Dumps
- **Purge**: Replicating the full `package.json`, `requirements.txt`, or `Cargo.toml` dependency list inside markdown.
- **Rationale**: The agent can inspect manifests directly when needed. In `GEMINI.md`, list only the top 3–5 foundational architectural pillars (e.g., `["Python 3.11+", "FastAPI", "PostgreSQL", "CTranslate2"]`).

### Directive 4: Purge Self-Documenting CLI Commands
- **Purge**: Documenting default invocations with no arguments or flags:
  - *Wrong*: `pytest`
  - *Wrong*: `cargo test`
  - *Wrong*: `npm run build`
  - *Wrong*: `git status`
- **Preserve**: Invocations with non-obvious flags, hardware targets, parallel worker isolation, required environment variables, or V4.0.0 contextual tooling flags:
  - *Correct*: `python -m pytest tests/unit -v --dist=loadscope`
  - *Correct*: `ffmpeg -hwaccel qsv -c:v h264_qsv -look_ahead 0 -i input.mp4`
  - *Correct*: `python scripts/context_compiler.py --files src/engine.py --task "Add NV12" --budget 600`
  - *Correct*: `python scripts/context_daemon.py --mode pre-commit --auto-patch`
  - *Correct*: `python scripts/verify_proofs.py --file GEMINI.md --workstream #3`

---

## 3. Dual-Dimension Context Budget Metrics

Every `GEMINI.md` is strictly evaluated along two dimensions: line count and estimated token density.

| Metric | Target (Green) | Warning Zone (Yellow) | Fatal Error (Red) |
| :--- | :--- | :--- | :--- |
| **Line Count** | $\le 350$ lines | $351 - 500$ lines (`WARN_BUDGET_APPROACHING`) | $> 500$ lines (`ERR_BUDGET_EXCEEDED`) |
| **Character Count** | $\le 10,000$ chars | $10,001 - 14,000$ chars | $> 14,000$ chars (`ERR_BUDGET_EXCEEDED`) |
| **Estimated Tokens** (`chars // 4`) | $\le 2,500$ tokens | $2,501 - 3,500$ tokens | $> 3,500$ tokens (`ERR_BUDGET_EXCEEDED`) |

### Strict Enforcement Behavior
- In standard mode (`validate_gemini_md.py`), warnings are printed to stderr, but execution succeeds (exit code `0`).
- In strict mode (`--strict`), any metric entering the Warning Zone or Fatal Error triggers an immediate exit code `1` and initiates the **Targeted Subtraction Protocol**.

---

## 4. Density Optimization Techniques

When compressing content to meet budget thresholds:

1. **Convert Prose to Tables**:
   - Long paragraphs describing modules consume 2-3x more tokens than a 3-column markdown table (`Component | Path | Purpose`).
2. **Prune ASCII Tree Depth**:
   - Limit file trees to depth 2. Never include individual test fixture files, assets, or vendor directories.
3. **Use Terse Directives**:
   - Replace *"It is strictly recommended that developers refrain from committing any unencrypted API tokens into the repository"* with:
   - *"NEVER commit plaintext API keys or credentials. Use `.env`."*
4. **Compile JIT Context Slices (`context_compiler.py`)**:
   - Never inject monolithic `GEMINI.md` files into narrow subagent tasks. Compile a Minimal Invariant Projection (MIP) clamped to the task token budget ($\le 600$ tokens):
     ```bash
     python scripts/context_compiler.py --files src/core.py --task "Refactor parser" --budget 600 --out .gemini/jit/context.md
     ```
5. **Guard Git Boundaries via Reality Daemon (`context_daemon.py`)**:
   - Prevent documentation sediment and signature drift at commit time with sub-100ms AST verification and auto-patching:
     ```bash
     python scripts/context_daemon.py --mode pre-commit --auto-patch
     ```
6. **Enforce Hermetic Task Proofs (`verify_proofs.py`)**:
   - Verify Section 5 workstream completion contracts with deterministic exit code checks, preventing premature completion:
     ```bash
     python scripts/verify_proofs.py --file GEMINI.md --workstream #1
     ```

---

## 5. The Sharding & Archive Taxonomy

When a context file (`GEMINI.md` or `CONTINUITY.md`) accumulates excessive volume exceeding density thresholds (>350 lines or >2,500 estimated tokens), execute automated context decomposition via `scripts/prune_context.py`.

The pruning engine applies a structured sharding and archiving taxonomy to relocate detailed specifications, finished progress, and excess historical records to dedicated documentation artifacts under `docs/`:

### 1. Rogue & Unsectioned Specifications → `docs/specs/<slug>.md`
- **Trigger**: Non-canonical H2 sections outside the strict 5-tier anatomy (e.g. extensive protocol definitions, streaming contracts, or feature deep-dives dumped directly into `GEMINI.md`).
- **Relocation Target**: `docs/specs/<kebab-case-slug>.md`
- **Invariant Harvest**: Permanent engineering rules, negative constraints (`NEVER`, `MUST`, `ALWAYS`), and hardware/environment dependencies are extracted into Section 3 (`## 🛑 Mandatory Engineering Constraints`) under `### Technical & Environmental Invariants`.
- **Link Citation**: A single-line GitHub-flavored alert pointer (`> [!NOTE] Detailed specification extracted to [slug](docs/specs/<slug>.md)`) is maintained under Section 2 (`## 🏗️ Architecture & Component Mapping`).

### 2. Completed Workstream Slices → `docs/workstreams/archive.md`
- **Trigger**: Section 5 (`## 🔄 Active Workstreams & Verification Status`) accumulates completed (`Done`) workstreams that clutter immediate agent attention.
- **Relocation Target**: `docs/workstreams/archive.md`
- **Behavior**: All completed workstream rows and their verification proof commands are preserved historically in chronological order in the archive.
- **Immediate Focus**: Only active workstreams (`In Progress`, `Pending`, `Blocked`) remain in `GEMINI.md` to maintain a tight topological DAG focus.

### 3. Surplus Learnings & Failure Modes → `docs/error-solving/understood-errors.md`
- **Trigger**: Section 5 `### Known Failure Modes & Project Learnings` grows beyond the density budget (e.g. dozens of entries totaling thousands of tokens).
- **Relocation Target**: `docs/error-solving/understood-errors.md`
- **Behavior**: The top-N (default 7) most recent and critical learnings are preserved in `GEMINI.md`. Surplus entries are appended to the project's permanent error catalog, formatted with error name, causes, solutions, and preventive rules.

### 4. Historical Session State → `docs/sessions/history/archive.md`
- **Trigger**: `CONTINUITY.md` accumulates extensive historical milestone records (`- Historical Archive:`), causing context bloat across consecutive agent sessions.
- **Relocation Target**: `docs/sessions/history/archive.md`
- **Behavior**: The canonical session ledger (`CONTINUITY.md`) retains only current active state (Goal, Constraints, Key Decisions, Done/Now/Next, Open Questions), keeping file size compact ($\le 40$ lines, $\le 1,000$ tokens) while preserving complete historical lineage in the archive.

### Pruning CLI Invocation
```bash
python scripts/prune_context.py [--file <path>] [--all] [--dry-run] [--apply] [--keep-learnings <N>]
```
- `--dry-run`: Analyzes density and previews line/token reductions in a terminal metrics table without mutating disk files.
- `--apply`: Executes atomic file writes with automatic rotating `.bak` backups (up to 3 generations).
- `--keep-learnings <N>`: Configures the threshold of learnings retained in Section 5 (default: 7).

