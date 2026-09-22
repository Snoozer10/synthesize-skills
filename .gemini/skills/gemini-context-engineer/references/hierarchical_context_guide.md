# Hierarchical Context Guide (DOX Subtree Sharding)

This guide documents the architecture, inheritance semantics, and operational protocols for hierarchical context sharding across monorepos and multi-component workspaces using `GEMINI.md` files.

---

## 1. Why Hierarchical Context?

In large codebases, polyglot repositories, or monorepos, a single monolithic `GEMINI.md` at the repository root suffers from two fundamental pathologies:
1. **Token Bloat & Dilution**: Monolithic context files quickly exceed density budgets (>350 lines / >2,500 tokens), diluting LLM attention on task-relevant invariants.
2. **Context Contamination**: Package-specific instructions (e.g., frontend CSS conventions vs. backend database migration rules) cross-contaminate disparate modules, inducing hallucinated imports and contradictory rules.

The **DOX (Documented Operations & Execution) Hierarchy** solves this by establishing an authoritative context tree: a root `GEMINI.md` for global invariants, and scoped child `GEMINI.md` files for discrete subtree boundaries.

---

## 2. When to Create a Child `GEMINI.md`

A directory subtree warrants its own child `GEMINI.md` when it represents a **durable boundary** with independent operational concerns:

| Criterion | Example Scenario | Shard Action |
| :--- | :--- | :--- |
| **Independent Runtime / Language** | Monorepo containing a Python backend in `services/api/` and a React frontend in `apps/web/` | Create `services/api/GEMINI.md` and `apps/web/GEMINI.md` |
| **Independent Build / Test Cycle** | An embedded microservice with its own `Dockerfile`, `Cargo.toml`, or test runner | Create `<component>/GEMINI.md` |
| **Isolated Architectural Invariants** | A package with strict compliance, security, or hardware constraints not applicable to sibling folders | Create `<package>/GEMINI.md` |
| **Autonomous Agent Delegations** | A subtree where subagents work autonomously in branched worktrees | Create `<module>/GEMINI.md` |

### CLI Sharding Command
To bootstrap a compliant child context file in any subdirectory:
```powershell
python <SKILL_DIR>/scripts/repo_indexer.py --shard path/to/subdir
```
This initializes `path/to/subdir/GEMINI.md` conforming to the 5-tier anatomy and indexes it into the parent's `### Child Context Index`.

---

## 3. Inheritance Rules & Authority Matrix

Hierarchical context enforces a strict parent-child inheritance model:

```text
┌─────────────────────────────────────────────────────────┐
│ Root GEMINI.md                                          │
│ - Global tech stack overview                            │
│ - Non-negotiable security & FerroxLabs invariants       │
│ - Child Context Index table                             │
└────────────────────────────┬────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
┌───────────────────────────┐ ┌───────────────────────────┐
│ Child GEMINI.md (Backend) │ │ Child GEMINI.md (Frontend)│
│ - Local domain models     │ │ - UI framework & state    │
│ - Database migration CLI  │ │ - Bundler & test commands │
│ - Backend failure modes   │ │ - Frontend failure modes  │
└───────────────────────────┘ └───────────────────────────┘
```

### The Three Authority Rules:
1. **Root Non-Negotiables are Inviolable**: A child `GEMINI.md` can never weaken, override, or contradict global constraints defined in root Section 3 (e.g., zero cloud SDKs, credential handling, commit safety).
2. **Nearest Owner Controls Local Details**: For package-specific directory structures, build flags, entrypoints, and localized failure modes, the nearest owning `GEMINI.md` takes precedence over root descriptions.
3. **No Unindexed Children**: Every child `GEMINI.md` must be registered in the parent or root `## 🏗️ Architecture & Component Mapping` under `### Child Context Index`. Unindexed child contexts trigger `WARN_CHILD_INDEX_INCOMPLETE` during validation.

---

## 4. The Read-Before-Edit Protocol

Autonomous agents must execute the deterministic Read-Before-Edit protocol prior to modifying any file:

1. **Identify Target Paths**: Determine all file paths expected to be inspected or edited during the task.
2. **Read Root Context**: Read root `./GEMINI.md` to establish global constraints, active workstreams, and discover indexed child contexts.
3. **Traverse Subtree Route**: Walk directory hierarchy from repository root to each target path.
4. **Ingest Nearest Child Context**: If any directory along the route contains a `GEMINI.md`, ingest the closest owning file as the binding local contract.
5. **Enforce Localized Invariants**: Merge root constraints with local constraints before authoring any code or running terminal commands.

---

## 5. DOX Hierarchical Closeout Pass Contract

Before completing any feature, PR, or multi-step task, the agent must perform a mandatory closeout pass:

1. **Scope Audit**: Check all modified files against the owning `GEMINI.md` boundary.
2. **Local Context Update**: If component boundaries, CLI flags, dependencies, or active workstreams in that subtree changed, update the nearest owning `GEMINI.md`.
3. **Child Index Refresh**: If a new child context was added, relocated, or removed, update the `### Child Context Index` in the parent `GEMINI.md`.
4. **Self-Healing Memory Ingestion**: If any bug, user correction, or hallucination was resolved during the task, formulate a single-line negative constraint (`"NEVER do X because Y; ALWAYS use Z"`) and append to the nearest `### Known Failure Modes & Project Learnings`.
5. **Strict Validation**: Run the validator to ensure all touched context files meet the 5-tier standard:
   ```powershell
   python <SKILL_DIR>/scripts/validate_gemini_md.py <path/to/GEMINI.md> --strict
   ```
