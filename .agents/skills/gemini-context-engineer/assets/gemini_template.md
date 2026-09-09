---
project_name: "project-name"
version: "4.0.0"
tech_stack:
  - "language/runtime"
  - "core-framework"
  - "primary-datastore-or-library"
rules:
  - "no-global-mutable-state"
  - "strict-typing"
  - "hermetic-unit-tests"
exclude_paths:
  - "dist"
  - "build"
  - "node_modules"
  - ".venv"
last_indexed: "YYYY-MM-DD"
generator: "gemini-context-engineer/v4.0.0"
---

# Project Context: project-name

## 🎯 Project Overview
<!--
GUIDANCE:
- Provide a high-density, 1-2 paragraph executive summary.
- Clearly state:
  1. What the project does (core domain and function).
  2. Who or what consumes it (end-users, internal microservices, CLI agents).
  3. Key operational capabilities and architectural goals.
- FORBIDDEN: Marketing hype, roadmaps, historical release notes, promotional filler.
-->

## 🏗️ Architecture & Component Mapping
<!--
GUIDANCE:
- Map directory topology, bounded contexts, and key dependencies.
- Prefer a compact markdown mapping table or shallow ASCII tree (depth <= 2) over long prose.
- Example table layout:
  | Directory / Module | Core Responsibility | Key Entrypoints & Interfaces |
  | :--- | :--- | :--- |
  | `src/core/` | Domain logic & state machine | `engine.py`, `StateContext` |
  | `src/api/`  | HTTP / RPC interface handlers | `routes.py`, `middleware.py` |
- Document data flow: Ingestion -> Transformation -> Output / Persistence.
- FORBIDDEN: Exhaustive file listings, auto-generated code dumps, third-party library internals.
-->

### Domain Lexicon & Ubiquitous Language
<!--
GUIDANCE:
- Canonical vocabulary defining domain terms to eliminate linguistic drift and semantic hallucinations.
- Mandatory columns: 'Term', 'Canonical Meaning', 'Forbidden Synonyms / Overloaded Usage'.
-->
| Term | Canonical Meaning | Forbidden Synonyms / Overloaded Usage |
| :--- | :--- | :--- |
| `Context Window` | LLM token input budget (attention boundary) | "Prompt cache", "Memory buffer" |
| `Deep Module` | High-leverage module (leverage >= 8.0) hiding complexity | "Fat controller", "Utility class" |
| `Invariant` | Non-inferable architectural rule causing breakage if violated | "Preference", "Guideline", "Tip" |

### Architectural Seams & Component Depth
<!--
GUIDANCE:
- AST leverage analysis (leverage = LOC / max(1, interface_count)).
- Deep modules (leverage >= 8.0) maximize power behind simple interfaces.
- Shallow modules (leverage < 2.5) should be monitored or refactored.
-->
| Module / Subtree | Interface Count | Implementation LOC | Leverage | Classification |
| :--- | :--- | :--- | :--- | :--- |
| `src/core/` | 4 | 320 | 80.0 | Deep Module |
| `src/storage/` | 3 | 195 | 65.0 | Deep Module |

### Child Context Index
<!--
GUIDANCE:
- Optional index for sharded monorepo subtrees or multi-component projects.
- Map each subtree component to its scoped child GEMINI.md.
-->
| Subtree / Scope | Context Path | Ownership & Core Responsibilities |
| :--- | :--- | :--- |
| `packages/core/` | `packages/core/GEMINI.md` | Core domain logic, state models, algorithmic contracts |
| `packages/api/`  | `packages/api/GEMINI.md`  | Route handlers, request validation, authentication gates |

## 🛑 Mandatory Engineering Constraints
<!--
GUIDANCE:
- Document non-negotiable architectural invariants and negative boundaries.
- Emphasize what agents MUST NEVER do (e.g., "NEVER commit plaintext secrets", "DO NOT import UI modules into core").
- Keep ONLY constraints that cannot be automatically caught by linters, formatters, or typecheckers.
- Apply the Inferable Rule: If a linter (Ruff, ESLint) or compiler (tsc, rustc) catches it, PURGE IT.
- Include data safety, transaction boundary rules, and platform-specific hazards.
- FORBIDDEN: Indentation/formatting rules, standard language idioms, stylistic debates.
-->

### FerroxLabs Cognitive Non-Negotiables
- **Anti-Sycophancy**: Disagree directly with false user premises, invalid assumptions, or hallucinated APIs. Never offer performative agreement.
- **Surgical Changes Only**: Modify strictly what is requested. Never perform unrequested refactorings, style churn, or scope creep.
- **Plausibility Is Not Correctness**: Code that "looks right" but is untested is assumed broken. Verify with executable tests before asserting success.

## 🛠️ Common Workflows & CLI Commands
<!--
GUIDANCE:
- Provide copy-pasteable, verified terminal commands.
- Focus on non-obvious flags, targeted suites, and essential environment setups.
- Standard categories: Build / Compile, Test Execution, Typecheck & Lint, Dev Server.
- Include mandatory pre-run environment variables.
- FORBIDDEN: Standard self-evident single-word commands without flags (e.g., plain `pytest`).
-->

### Multi-Agent Orchestration & Quality Gates
<!--
GUIDANCE:
- OpenCode & Antigravity Multi-Agent Task Routing:
  - Coordinator (Tier 1: Claude 3.7 Sonnet / Gemini Pro): High-level decomposition, plan verification.
  - Executor (Tier 2: Gemini Flash / DeepSeek V3): Fast surgical implementation, localized tests.
- Quality Gates: Every task must satisfy (1) Unit tests passing, (2) Linter clean, (3) validate_gemini_md.py --strict --reality.
-->

## 🔄 Active Workstreams & Verification Status
<!--
GUIDANCE:
- DAG Tracer-Bullet workstream table modeling topological execution order.
- Columns: 'ID', 'Workstream Slice', 'Status', 'Blocked By', 'Proof Command'.
- TopologicalSorter detects cycles. Unblocked tasks execute first.
- FORBIDDEN: Speculative multi-quarter roadmaps or wishlist features (move those to ROADMAP.md).
-->

| ID | Workstream Slice | Status | Blocked By | Proof Command |
| :--- | :--- | :--- | :--- | :--- |
| `#1` | Core Domain & State Model Slice | Done | - | `pytest tests/unit/test_domain.py -v` |
| `#2` | Ingestion Pipeline & Serialization | In Progress | `#1` | `pytest tests/unit/test_pipeline.py -v` |
| `#3` | API & CLI Interface Gate | Pending | `#2` | `python scripts/validate_api.py --strict` |

### Known Failure Modes & Project Learnings
<!--
GUIDANCE:
- Self-Healing Memory Loop: Append single-line negative constraints when bugs or hallucinations occur.
- Format: - [LEARNING-XXX]: NEVER do X because Y; ALWAYS use Z.
- Prune oldest entries when total file exceeds 350 lines.
-->
- [LEARNING-001]: NEVER assume X because Y; ALWAYS verify Z.
