# Deep Modules, Frontier Grilling, and Dual-Axis Context Engineering

This guide documents the core software engineering principles underpinning **gemini-context-engineer v3.0.0 Pro Max**: John Ousterhout and Pocock Deep Module analysis, the Frontier Grilling Engine, Tracer-Bullet DAG Workstream orchestration, and Dual-Axis Reality Validation.

---

## 1. Deep Modules vs Shallow Modules: Leverage and Locality

### Theoretical Foundation
In *A Philosophy of Software Design*, John Ousterhout established that the most critical metric for modular decomposition is the ratio between the benefit provided by a module and the cognitive cost of its interface. Pocock formalised this in modern agentic architectures as **Interface Leverage** and **Information Locality**.

```text
┌────────────────────────────────────────────────────────┐
│                   SHALLOW MODULE                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │     Wide, Leaky Interface (Many Functions/Args)  │  │
│  └─────────────────────────┬────────────────────────┘  │
│                            │                           │
│  ┌─────────────────────────▼────────────────────────┐  │
│  │   Thin Implementation (Low Value, Pass-Through)  │  │
│  └──────────────────────────────────────────────────┘  │
│   Leverage < 2.5: High cognitive load, minimal abstraction │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                    DEEP MODULE                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │          Simple, Narrow, Stable Interface        │  │
│  └─────────────────────────┬────────────────────────┘  │
│                            │                           │
│  ┌─────────────────────────▼────────────────────────┐  │
│  │   Rich, Deep Implementation Body                 │  │
│  │   - Internal state machine                       │  │
│  │   - Comprehensive edge-case handling             │  │
│  │   - Autonomous error recovery                    │  │
│  └──────────────────────────────────────────────────┘  │
│   Leverage >= 8.0: Maximum power behind minimal cognitive cost │
└────────────────────────────────────────────────────────┘
```

### Mathematical Formulation
The AST leverage metric quantifies architectural depth:

$$\text{Leverage} = \frac{\text{LOC}_{\text{impl}}}{\max(1, N_{\text{interface}})}$$

Where:
- $\text{LOC}_{\text{impl}}$: Total non-empty, non-comment lines of implementation code.
- $N_{\text{interface}}$: Number of public entrypoints (classes, public functions) plus their exposed parameter count:
  $$N_{\text{interface}} = \sum_{\text{public funcs}} (1 + N_{\text{params}}) + \sum_{\text{public classes}} 1$$

### Classification Thresholds
- **Deep Module ($\text{Leverage} \ge 8.0$)**: The module hides immense complexity behind a simple abstraction. Callers and AI agents can invoke it with high confidence without understanding internal mechanics.
- **Shallow Module ($\text{Leverage} < 2.5$ and $N_{\text{interface}} \ge 3$)**: Leaky abstractions, repetitive boilerplate shims, or pass-through adapters. They burden context windows with function signatures that provide negligible implementation value.

### Autonomous AST Extraction
`repo_indexer.py` analyzes Python codebases using the standard library `ast` module:
1. Parses AST nodes (`FunctionDef`, `AsyncFunctionDef`, `ClassDef`).
2. Filters out private symbols (names starting with `_`).
3. Tallies positional and keyword arguments (`args.args`, `args.kwonlyargs`).
4. Computes leverage and surfaces top 5 deep and shallow components under `architectural_health`.

---

## 2. Frontier Grilling Engine

### Motivation: Combatting Sycophancy and Premature Convergence
Autonomous agents often suffer from **sycophancy** (agreeing with flawed user premises) or **premature convergence** (implementing the first plausible path without exploring trade-offs). When context files lack explicit domain boundaries or hardware invariants, agents hallucinate assumptions.

The **Frontier Grilling Engine** acts as an assertive architectural interviewer. It identifies unsettled design frontiers and forces explicit alignment before coding begins.

### The Design Tree and Frontier
```text
Root: System Goal
 ├── Node 1: Architecture Pattern [RESOLVED: Pipeline]
 ├── Node 2: Data Persistence [RESOLVED: Filesystem JSON]
 └── Node 3: Execution Runtime [FRONTIER]
      ├── Option A: Browser CDP Loopback (127.0.0.1:9222)
      └── Option B: Cloud Headless Playwright
```
The **Frontier** consists of leaf nodes where:
- Critical invariants are missing or unspecified.
- Conflicting assumptions exist between manifests and documentation.
- Decisions have high downstream irreversibility.

### Grilling Protocol
1. **Trigger**:
   - Automated during `CREATE` when Section 3 invariants or primary stack files are missing.
   - Manual when invoked with `python repo_indexer.py --grill`.
2. **Sequential Rounds**:
   - Maximum **3 questions** per round.
   - Strictly maximum **3 rounds** total.
   - Can be bypassed entirely with `--yes` or `--skip-grill`.
3. **Structured Question Format**:
   Each question presents a clear statement of ambiguity paired with an opinionated, evidence-backed recommendation:
   ```markdown
   ❓ **Q1** - **<Decision Title>**: <Context and specific ambiguity>
   ➡️ **<Recommended Answer>**: <Concrete proposal with technical rationale>
   ```
4. **Crystallization into Section 3**:
   Once answered, agreed choices are transcribed directly into `## 🛑 Mandatory Engineering Constraints` as non-inferable negative boundaries (`NEVER X; ALWAYS Y`).

---

## 3. Tracer-Bullet Vertical Slices & DAG Orchestration

### The Tracer-Bullet Philosophy
Derived from *The Pragmatic Programmer*, a **Tracer Bullet** is a minimal, complete end-to-end slice through all architectural layers (UI/CLI $\to$ Logic Engine $\to$ Storage/Integration $\to$ Automated Verification). Unlike a horizontal architectural prototype, a tracer bullet is production code that establishes immediate feedback loops.

### DAG Dependency Modeling
In complex multi-agent systems, workstreams cannot be managed as flat task lists. Flat lists cause race conditions, deadlocks, and out-of-order execution across subagents.

Workstreams in `GEMINI.md` Section 5 are modeled as a **Directed Acyclic Graph (DAG)**:
```text
  [#1: AST Analyzer] ──► [#3: Grilling CLI]
          │                     │
          ▼                     ▼
  [#2: DAG Sorter]   ──► [#4: Dual-Axis Reality]
```

### Table Representation
```markdown
| ID | Workstream Slice | Status | Blocked By |
| :--- | :--- | :--- | :--- |
| `#1` | Core AST Analyzer & Leverage Metrics | Done | - |
| `#2` | DAG Cycle Detection Engine | Done | - |
| `#3` | Frontier Grilling CLI Integration | Done | `#1` |
| `#4` | Dual-Axis Reality Drift Validation | In Progress | `#1`, `#2` |
```

### Topological Cycle Detection with `graphlib`
Circular dependencies (`#1` blocked by `#2`, `#2` blocked by `#1`) cause multi-agent deadlock. `validate_gemini_md.py` verifies acyclicity using Python's standard library `graphlib.TopologicalSorter`:
```python
import graphlib

graph = {
    "#1": set(),
    "#2": set(),
    "#3": {"#1"},
    "#4": {"#1", "#2"}
}
ts = graphlib.TopologicalSorter(graph)
ts.prepare()  # Raises graphlib.CycleError if any loop exists
```
If a cycle is detected, the validator emits `ERR_DAG_CYCLE`, halting the pipeline until dependencies are untangled.

---

## 4. Dual-Axis Context Validation

Traditional linters validate only syntax or internal consistency. `gemini-context-engineer` enforces **Dual-Axis Validation** to prevent architectural drift.

```text
                 AXIS 1: STANDARDS & DAG
      (Micro-YAML, 5-Tier Emojis, Token Budgets, DAG Cycles)
                           │
                           ▼
                    ┌─────────────┐
                    │ GEMINI.md   │
                    └─────────────┘
                           ▲
                           │
                 AXIS 2: REALITY DRIFT
     (Ground-Truth Filesystem Verification via --reality)
```

### Axis 1: Standards & DAG Integrity (Internal Consistency)
- **Frontmatter Schema**: Validates micro-YAML syntax, CRLF line endings, and mandatory keys (`project_name`, `version`, `tech_stack`, `rules`, `exclude_paths`, `last_indexed`).
- **5-Tier Heading Anatomy**: Enforces single H1 and exact 5x H2 headers with mandatory emojis (`🎯`, `🏗️`, `🛑`, `🛠️`, `🔄`).
- **Token Density Guard**: Dual-budget thresholds (Target $\le 350$ lines / $\le 2,500$ tokens; Hard limit $\le 500$ lines / $\le 3,500$ tokens).
- **Domain Lexicon Schema**: If `### Domain Lexicon & Ubiquitous Language` exists in Section 2, ensures presence of `Term` and `Canonical Meaning` table columns.
- **DAG Workstream Acyclicity**: Extracts task IDs and `Blocked By` references, verifying topological feasibility with `TopologicalSorter`.

### Axis 2: Reality Drift Validation (`--reality`) (External Alignment)
- **The Problem**: Over time, repositories evolve. Files are renamed, directories moved, and modules deleted. Context files that retain stale links mislead agents into hallucinating legacy components.
- **Verification Protocol**:
  1. Parses all markdown hyperlinks and relative path citations in Section 2 (`## 🏗️ Architecture & Component Mapping`).
  2. Resolves each relative target against `repo_root`.
  3. Tests existence with `Path.exists()`.
  4. Any missing file or phantom directory triggers `WARN_REALITY_DRIFT: Documented component does not exist on disk: '<path>'`.
- **Enforcement**: When run with `validate_gemini_md.py --strict --reality`, reality warnings become hard errors, guaranteeing that documented architecture 100% mirrors physical repository state.
