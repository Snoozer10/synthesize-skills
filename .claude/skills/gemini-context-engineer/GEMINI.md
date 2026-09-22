---
project_name: "gemini-context-engineer"
version: "4.0.0"
tech_stack:
  - "python"
  - "antigravity-cli"
  - "standard-library"
rules:
  - "strict-5-tier-anatomy"
  - "zero-external-dependencies"
  - "sub-150ms-indexer-latency"
  - "inferable-rule-enforcement"
  - "dual-dimension-budgeting"
  - "dox-hierarchical-sharding"
  - "ferroxlabs-anti-sycophancy"
  - "frontier-grilling-invariants"
  - "dag-tracer-bullet-orchestration"
  - "dual-axis-reality-validation"
exclude_paths:
  - ".git"
  - "__pycache__"
  - "*.bak"
  - "tests/fixtures"
last_indexed: "2026-09-03"
generator: "gemini-context-engineer/v4.0.0"
---

# Project Context: gemini-context-engineer

## 🎯 Project Overview
`gemini-context-engineer` is an enterprise-grade, zero-dependency context management system for Google Antigravity and Claude Code. Version 4.0.0 Enterprise enforces deterministic 5-tier `GEMINI.md` architectures, JIT context compilation (MIP bounding <= 600 tokens), sub-100ms VCS Git reality sync, executable workstream proofs, frontier grilling, AST leverage metrics, DAG tracer-bullet orchestration, and dual-axis reality validation (<350 lines, <2,500 tokens).

## 🏗️ Architecture & Component Mapping
The skill operates as a standalone Python standard library module encompassing CLI automation scripts, golden templates, reference guides, and an automated test suite.

| Path | Role | Description |
| :--- | :--- | :--- |
| [SKILL.md](SKILL.md) | Skill Spec | Contract, 5-tier anatomy, grilling protocol, DOX closeout |
| [assets/gemini_template.md](assets/gemini_template.md) | Golden Template | Strict 5-tier template with V4.0.0 Enterprise annotations |
| [references/pocock_deep_modules_and_grilling.md](references/pocock_deep_modules_and_grilling.md) | Architecture | AST module leverage and frontier grilling guide |
| [references/token_budget_heuristics.md](references/token_budget_heuristics.md) | Density Spec | Inferable Rule decision tree and subtraction heuristics |
| [references/migration_guide.md](references/migration_guide.md) | Migration | Rotating backups and Section 5 Proof Command upgrade |
| [references/hierarchical_context_guide.md](references/hierarchical_context_guide.md) | Hierarchy | Subtree sharding and Read-Before-Edit protocol |
| [references/cross_ecosystem_federation.md](references/cross_ecosystem_federation.md) | Federation | SSOT alignment via symlinks and pointer shims |
| [references/jit_compiler_guide.md](references/jit_compiler_guide.md) | JIT Compiler | Minimal Invariant Projection token bounding (<=600 tokens) |
| [references/vcs_daemon_guide.md](references/vcs_daemon_guide.md) | VCS Daemon | Sub-100ms AST change detection & pre-commit auto-patch |
| [references/executable_proofs_guide.md](references/executable_proofs_guide.md) | Proofs Guide | Subprocess exit-0 gate & anti-premature completion |
| [scripts/__version__.py](scripts/__version__.py) | Version | Semantic version authority (v4.0.0) |
| [scripts/repo_indexer.py](scripts/repo_indexer.py) | Indexer | Scanner with AST leverage analysis and `--grill` |
| [scripts/validate_gemini_md.py](scripts/validate_gemini_md.py) | Validator | Dual-axis auditor for schemas, budgets, and `--reality` |
| [scripts/context_compiler.py](scripts/context_compiler.py) | JIT Compiler | Task context projection engine enforcing token budget |
| [scripts/context_daemon.py](scripts/context_daemon.py) | Reality Daemon | Git pre-commit daemon detecting signature drift & patching |
| [scripts/verify_proofs.py](scripts/verify_proofs.py) | Proof Runner | Subprocess gate enforcing deterministic workstream proofs |
| [scripts/run_evals.py](scripts/run_evals.py) | Benchmark | Automated runner verifying all 7 formal eval scenarios |

### Domain Lexicon & Ubiquitous Language
| Term | Canonical Meaning | Forbidden Synonyms / Overloaded Usage |
| :--- | :--- | :--- |
| `Context Window` | LLM token input budget (attention boundary) | "Prompt cache", "Memory buffer" |
| `Deep Module` | High-leverage module (leverage >= 8.0) hiding complexity | "Fat controller", "Utility class" |
| `Shallow Module` | Leaky module (leverage < 2.5) with low abstraction value | "Thin service", "Helper wrapper" |
| `Frontier Grilling` | Structured inquiry resolving uncommitted design decisions | "Brainstorming", "Chit-chat" |
| `Tracer Bullet` | End-to-end vertical slice verifying architecture in production | "Throwaway prototype", "Spike" |
| `Reality Drift` | Discrepancy between documented context and physical filesystem | "Outdated docs", "Desync" |

### Architectural Health & Deep Modules
| Module / Subtree | Interface Count | Implementation LOC | Leverage | Classification |
| :--- | :--- | :--- | :--- | :--- |
| [scripts/validate_gemini_md.py](scripts/validate_gemini_md.py) | 15 | 410 | 27.33 | Deep Module |
| [scripts/verify_proofs.py](scripts/verify_proofs.py) | 7 | 107 | 15.29 | Deep Module |
| [scripts/context_daemon.py](scripts/context_daemon.py) | 22 | 245 | 11.14 | Deep Module |
| [scripts/run_evals.py](scripts/run_evals.py) | 28 | 302 | 10.79 | Deep Module |
| [scripts/repo_indexer.py](scripts/repo_indexer.py) | 28 | 282 | 10.07 | Deep Module |
| [scripts/context_compiler.py](scripts/context_compiler.py) | 43 | 294 | 6.84 | Balanced Module |

## 🛑 Mandatory Engineering Constraints
1. **Zero External Dependencies**: All scripts in `scripts/` MUST use Python standard library modules only (`sys`, `os`, `pathlib`, `json`, `re`, `argparse`, `shutil`, `datetime`, `subprocess`, `ast`, `graphlib`, `tomllib`). NEVER install or import third-party packages.
2. **Strict 5-Tier Markdown Anatomy**: Files MUST contain a single `# Project Context: <name>` H1 and exactly 5 H2 headers with mandatory emojis: `🎯 Project Overview`, `🏗️ Architecture & Component Mapping`, `🛑 Mandatory Engineering Constraints`, `🛠️ Common Workflows & CLI Commands`, and `🔄 Active Workstreams & Verification Status`.
3. **Execution Latency Budget**: `repo_indexer.py` MUST complete in <150ms using Git-native `git ls-files`.
4. **Safety Traversal Gate**: `repo_indexer.py` MUST reject indexing `Path.home()` without explicit `--scope project`.
5. **Non-Destructive Rotating Backups**: System MUST create timestamped backups (`GEMINI.md.<YYYYMMDD_HHMMSS>.bak`) retaining maximum 3 generations.
6. **Inferable Rule Enforcement**: Never document compiler/linter enforceable rules, whitespace rules, or raw dependency dumps.
7. **DAG Acyclicity Guarantee**: Section 5 workstreams MUST form a strictly acyclic graph validated by `graphlib.TopologicalSorter`.

### FerroxLabs Cognitive Non-Negotiables
- **Anti-Sycophancy**: Disagree directly with false user premises, invalid assumptions, or hallucinated APIs. Never offer performative agreement.
- **Surgical Changes Only**: Modify strictly what is requested. Never perform unrequested refactorings, style churn, or scope creep.
- **Plausibility Is Not Correctness**: Code that "looks right" but is untested is assumed broken. Evidence before assertions: always verify with compiler, linter, or test execution.

## 🛠️ Common Workflows & CLI Commands
Executable with Python 3.11+ standard library:

```bash
# Index repo with AST leverage analysis
python scripts/repo_indexer.py --root . --json

# Probe missing invariants via Frontier Grilling
python scripts/repo_indexer.py --root . --grill --json

# Validate GEMINI.md (strict mode + reality drift check)
python scripts/validate_gemini_md.py GEMINI.md --strict --reality

# Compile JIT context slice bounded to 600 tokens
python scripts/context_compiler.py --files scripts/repo_indexer.py --budget 600

# VCS daemon pre-commit reality sync with auto-patching
python scripts/context_daemon.py --mode pre-commit --auto-patch

# Execute deterministic workstream proof
python scripts/verify_proofs.py --file GEMINI.md --workstream #1

# Run all 7 formal benchmark evaluation scenarios
python scripts/run_evals.py

# Run unit test suite
python -m unittest discover -s tests -v
```

### Multi-Agent Orchestration & Quality Gates
- **Coordinator / Architect (Tier 1: Claude 3.7 Sonnet / Gemini Pro)**: Task decomposition, cross-file architectural plans, PR review.
- **Executor / Coder (Tier 2: Gemini Flash / DeepSeek V3)**: Surgical implementation, localized unit tests, format fixes.
- **Quality Gates**: Every turn must pass: (1) Unit tests green, (2) Linters clean, (3) `validate_gemini_md.py --strict --reality` with zero errors and zero warnings.

## 🔄 Active Workstreams & Verification Status
| ID | Workstream Slice | Status | Blocked By | Proof Command |
| :--- | :--- | :--- | :--- | :--- |
| `#1` | AST Leverage Analysis & Health Metric | Done | - | `python -m unittest tests/test_indexer.py` |
| `#2` | TopologicalSorter DAG Cycle Detection | Done | - | `python -m unittest tests/test_validator.py` |
| `#3` | JIT Context Compiler Slicing & Clamping | Done | `#1` | `python -m unittest tests/test_context_compiler.py` |
| `#4` | VCS Continuous Reality Daemon & Auto-Patch | Done | `#1`, `#2` | `python -m unittest tests/test_context_daemon.py` |
| `#5` | Executable Workstream Proofs Engine | Done | `#2` | `python -m unittest tests/test_verify_proofs.py` |
| `#6` | Formal Benchmark Suite & Evals | Done | `#3`, `#4`, `#5` | `python scripts/run_evals.py` |

### Known Failure Modes & Project Learnings
- [LEARNING-001]: NEVER assume `os.symlink` target exists; ALWAYS verify path before checking `.exists()` on broken links.
- [LEARNING-002]: NEVER rely on unindexed child context files; ALWAYS register child `GEMINI.md` in Section 2 `### Child Context Index`.
- [LEARNING-003]: NEVER parse full markdown for pointer shims; ALWAYS look for `<!-- AGENT-SYNC: GEMINI.md -->` header comment.
- [LEARNING-004]: NEVER accept circular workstream blockers in Section 5; ALWAYS validate with `graphlib.TopologicalSorter`.
- [LEARNING-005]: NEVER retain stale architectural links in Section 2; ALWAYS enforce `--reality` validation against live filesystem.
