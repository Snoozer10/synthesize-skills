# repo-standards-engineer Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `repo-standards-engineer` into an enterprise-grade multi-paradigm Codebase Standards, AST Contract & Compliance Verification Engine with rich semantic assertions, automated standards-driven spec shaping, compliance drift detection, and rigorous pressure testing.

**Architecture:** Extend the Python standard library AST and pattern discovery pipeline to deeply understand modern typed architectures (Pydantic, dataclasses, TypedDict, custom exception hierarchies, TypeScript interfaces/types/enums), introduce a new compliance auditing engine (`check_compliance.py`) to verify diffs against discovered envelopes, expand deterministic verification contracts (`verify_spec.py`) with rich assertions (`file_contains`, `json_matches`, `ast_symbol_present`, `regex_matches`), and auto-wire discovered standards into generated specs (`shape_spec.py --from-standards`).

**Tech Stack:** Python 3.11+ (100% Python Standard Library: `ast`, `re`, `json`, `pathlib`, `hashlib`, `subprocess`, `argparse`, `difflib`, `tempfile`). Zero pip dependencies.

**Spec:** Canonical skill at `.agents/skills/repo-standards-engineer/` and test harness in `tests/test_standards_engine.py`.

---

## 1. Research & Ecosystem State of the Art

### 1.1 The Role of Standards in Agentic Workflows
In multi-agent systems, agents frequently produce code that is syntactically valid but architecturally alien to the host codebase:
- Inventing new error codes (`ERR_ITEM_NOT_FOUND` vs existing `ERR_NOT_FOUND`).
- Mangling response envelopes (returning `{"items": [...]}` instead of `{"status": "success", "data": {"items": [...]}, "meta": {...}}`).
- Breaking naming conventions or introducing unapproved query methods (`db.raw()` instead of `db.fetch_one()`).

Current agent architectures either bloat the prompt with massive architectural documentation (wasting precious context budget) or suffer from high hallucination rates. `repo-standards-engineer` solves this via **JIT Minimum Instruction Packet (MIP <= 600 tokens)** discovery and deterministic verification contracts.

### 1.2 Multi-Paradigm AST Extraction vs External Parsers
External tools like `tree-sitter` or `libcst` introduce compiled C-extensions or heavy pip dependencies, which violates the strict **Stdlib-Only constraint** of this repository.
By leveraging Python's built-in `ast` module combined with high-precision regex state machines:
1. **Python**: Can inspect full AST (`ClassDef`, `AnnAssign`, `FunctionDef`, `Decorator`, `Return`, `Dict`, `Call`) without third-party libraries.
2. **TypeScript / JavaScript**: Can extract structured interfaces (`interface ... { ... }`), type aliases (`type ApiResponse<T> = ...`), enums (`enum ErrorCode`), and object returns via multi-line regex tokenizers without node/npm overhead.
3. **Go / Rust / SQL**: Can extract error constants, struct tags, and query methods via regex lexers.

---

## 2. Review & Audit of Existing Implementation

### 2.1 Component-by-Component Audit

| File | Current Role | Current Limitations / Weaknesses |
| :--- | :--- | :--- |
| `scripts/discover_standards.py` | AST/regex scanner with SHA-256 caching | - Only detects basic `Enum` subclassing or classes with "Error"/"Code" in name.<br>- Ignores Pydantic models (`BaseModel`), dataclasses, TypedDict.<br>- Only inspects dict literals in `visit_Return`; misses helper constructors or wrapper returns.<br>- Text scanning for JS/TS is brittle (`ERR_[A-Z0-9_]+` only; misses TS enums and types).<br>- Cache invalidation only checks file content hash, not parser version. |
| `scripts/index_standards.py` | Indexes functions and classes to files/lines | - Only indexes Python `FunctionDef` and `ClassDef`.<br>- No symbol querying CLI (e.g. `python index_standards.py --query <symbol>`).<br>- No cross-referencing between error code definition site and usage site. |
| `scripts/inject_standards.py` | Formats standards into MIP <= 600 tokens | - Token heuristic (`words * 1.3`) is slightly coarse.<br>- Only 4 fixed sections (Envelope, Errors, DB, Naming).<br>- No file-targeted injection (e.g., injecting only standards relevant to API files vs DB files). |
| `scripts/shape_spec.py` | Generates `specs/<slug>/` `SPEC.md` and `VERIFICATION.json` | - Doesn't leverage discovered standards when generating criteria.<br>- `VERIFICATION.json` schema is limited to `files_exist` and `commands`. |
| `scripts/verify_spec.py` | Executes deterministic contract assertions | - Only 2 assertion types: `files_exist` and `commands`.<br>- Shell execution (`commands`) is susceptible to platform shell nuances.<br>- No built-in semantic assertions (`file_contains`, `json_matches`, `ast_symbol_present`, `regex_matches`). |
| `tests/test_standards_engine.py` | Engine tests | - Only 3 tests covering happy-path discovery, token bounding, and basic shape/verify.<br>- 0 edge-case tests, 0 negative tests for syntax errors, 0 multi-file complexity tests. |

### 2.2 Critical Vulnerabilities & Architectural Bottlenecks
1. **Compliance Blind Spot**: The skill can discover standards and inject them into context, but it has **no mechanism to audit newly written code against those standards**. An agent can violate the response envelope completely, and nothing catches it unless manual shell commands are handcrafted in `VERIFICATION.json`.
2. **Shallow AST Extraction**: Modern Python projects rarely use raw `Enum` classes with dict returns; they use Pydantic `BaseModel` schemas, FastAPI `response_model`, and custom exception classes. `discover_standards.py` completely misses these.
3. **Contract Expressiveness Bottleneck**: Requiring users to write shell command strings for every check (e.g., `python -c "import json; ..."` or `grep ...`) is fragile across Windows (PowerShell) and POSIX (bash). Native semantic assertions are urgently needed.

---

## 3. Architectural Recommendations

1. **Recommendation 1: Modern Typed AST Discovery Engine**
   - Enhance `PythonASTVisitor` to detect:
     - Pydantic models & Dataclasses (`BaseModel`, `@dataclass`, `TypedDict`).
     - Custom exception classes (`class *Error(Exception)` or `class *(..., Exception)`).
     - Response wrapper functions and FastAPI route decorators.
   - Enhance text scanning for TypeScript/JavaScript to extract `enum ErrorCode`, `type Response = ...`, and `interface ApiResponse`.
2. **Recommendation 2: Built-in Compliance Checker (`check_compliance.py`)**
   - Create a deterministic compliance auditor that scans staged git diffs or specific files and checks:
     - Do return dicts/models match the discovered response envelope?
     - Are thrown or returned error codes members of the discovered error code set?
     - Are prohibited query patterns or functions used?
3. **Recommendation 3: Rich Semantic Verification Contract Assertions**
   - Expand `VERIFICATION.json` schema to natively support:
     - `files_exist`: list of required paths (existing).
     - `file_contains`: `{path: str, substrings: list[str]}`.
     - `regex_matches`: `{path: str, pattern: str}`.
     - `json_matches`: `{path: str, subset: dict}`.
     - `ast_symbol_present`: `{file: str, symbol: str, type: "class"|"function"|"variable"}`.
     - `commands`: list of shell commands (existing).
4. **Recommendation 4: Standards-Driven Spec Auto-Scaffolding**
   - Add `--from-standards` flag to `shape_spec.py` to auto-populate acceptance criteria and contract assertions with the repo's discovered response envelope and error code rules.
5. **Recommendation 5: Symbol Query & Reverse Indexing**
   - Add `--query <symbol>` and `--search <term>` flags to `index_standards.py` for instant terminal inspection of where standards and symbols are defined.
6. **Recommendation 6: Formal Pressure Test Suite & Evals Benchmark**
   - Build `tests/test_standards_engine_pressure.py` with multi-paradigm test cases (Pydantic, TypeScript, compliance drift, rich contracts).
   - Add formal evals harness in `.agents/skills/repo-standards-engineer/evals/` matching the enterprise standard in `gemini-context-engineer`.

---

## 4. Phased Implementation Plan

### Task 1: Modern Multi-Paradigm AST & Pattern Discovery Engine

**Files:**
- Modify: `.agents/skills/repo-standards-engineer/scripts/discover_standards.py`
- Test: `tests/test_standards_engine.py`

**Interfaces:**
- `PythonASTVisitor`: Detects Pydantic `BaseModel`, `@dataclass`, `TypedDict`, custom `Exception` classes, and function annotations.
- `scan_ts_file(path: Path) -> dict`: Extracts TypeScript interfaces, types, enums, and object literals via regex tokenizer.
- `discover_standards(root: Path, force: bool = False) -> dict`: Merges multi-paradigm discoveries into structured `standards_cache.json`.

- [ ] **Step 1: Write failing unit test for modern AST discovery (Pydantic, dataclasses, TypedDict, TS interfaces)**
  In `tests/test_standards_engine.py`, add `test_pydantic_and_typed_ast_discovery()`:
  ```python
  def test_pydantic_and_typed_ast_discovery():
      # Sets up files with Pydantic BaseModel, Dataclass, TypedDict, and TS enum/interface
      # Verifies discover_standards extracts schemas, response envelopes, and error codes
  ```
- [ ] **Step 2: Run test to verify it fails**
  Run: `python tests/test_standards_engine.py`
  Expected: FAIL on missing Pydantic/TS extraction.
- [ ] **Step 3: Implement enhanced AST & TS visitors in `discover_standards.py`**
  - Add AST visitors for `ast.AnnAssign`, class bases (`BaseModel`, `TypedDict`), class decorators (`@dataclass`).
  - Add exception hierarchy detector (`ast.ClassDef` where base ends with `Exception` or `Error`).
  - Add `scan_ts_file()` for `.ts`, `.tsx`, `.js`, `.jsx` parsing enums, interfaces, and type aliases.
- [ ] **Step 4: Run test to verify it passes**
  Run: `python tests/test_standards_engine.py`
  Expected: PASS.
- [ ] **Step 5: Commit changes**
  `git commit -m "feat(standards-engineer): enhance AST discovery for Pydantic, dataclasses, and TypeScript"`

---

### Task 2: Rich Semantic Assertion Types in Executable Contracts

**Files:**
- Modify: `.agents/skills/repo-standards-engineer/scripts/verify_spec.py`
- Modify: `.agents/skills/repo-standards-engineer/templates/verification_template.json`
- Test: `tests/test_standards_engine.py`

**Interfaces:**
- `verify_spec(spec_dir: Path, ...)`:
  - Evaluates `files_exist: list[str]`.
  - Evaluates `file_contains: list[{"file": str, "contains": list[str]}]`.
  - Evaluates `regex_matches: list[{"file": str, "pattern": str}]`.
  - Evaluates `json_matches: list[{"file": str, "subset": dict}]`.
  - Evaluates `ast_symbol_present: list[{"file": str, "name": str, "type": str}]`.
  - Evaluates `commands: list[str]`.

- [ ] **Step 1: Write failing unit test for rich semantic assertions**
  In `tests/test_standards_engine.py`, add `test_rich_semantic_contract_assertions()`:
  Test file content checks, regex matching, json subset matching, and AST symbol presence without shell commands.
- [ ] **Step 2: Run test to verify it fails**
  Run: `python tests/test_standards_engine.py`
  Expected: FAIL with unrecognized assertion keys.
- [ ] **Step 3: Implement semantic assertion executors in `verify_spec.py`**
  - Implement `_check_file_contains(repo_root, assertion)`.
  - Implement `_check_regex_matches(repo_root, assertion)`.
  - Implement `_check_json_matches(repo_root, assertion)` with recursive subset matching.
  - Implement `_check_ast_symbol_present(repo_root, assertion)` using Python `ast.walk`.
  - Update `verification_template.json` schema documentation.
- [ ] **Step 4: Run test to verify it passes**
  Run: `python tests/test_standards_engine.py`
  Expected: PASS.
- [ ] **Step 5: Commit changes**
  `git commit -m "feat(standards-engineer): implement rich semantic assertion engine in verify_spec"`

---

### Task 3: Standards Compliance & Drift Checker (`check_compliance.py`)

**Files:**
- Create: `.agents/skills/repo-standards-engineer/scripts/check_compliance.py`
- Test: `tests/test_standards_engine.py`

**Interfaces:**
- `check_compliance(root: Path, target_files: list[Path] = None, standards: dict = None) -> tuple[bool, dict]`:
  - Scans files or git diff for:
    - Undeclared error codes.
    - Malformed response envelopes.
    - Prohibited query patterns.
    - Naming convention violations.
  - Returns `(is_compliant: bool, report: dict)`.
  - CLI: `python scripts/check_compliance.py [--staged] [--files ...] [--json]`

- [ ] **Step 1: Write failing unit test for compliance checker**
  In `tests/test_standards_engine.py`, add `test_standards_compliance_checker()`:
  - Create compliant file (matches envelope & error codes) -> exits 0.
  - Create violating file (alien error code & broken envelope) -> exits 1 with detailed violations.
- [ ] **Step 2: Run test to verify it fails**
  Run: `python tests/test_standards_engine.py`
  Expected: FAIL on missing `check_compliance.py`.
- [ ] **Step 3: Implement `check_compliance.py`**
  - Compare file AST against discovered `response_envelope` and `error_codes`.
  - Support `--staged` via `git diff --name-only --cached`.
  - Format terminal output with clear violation pointers.
- [ ] **Step 4: Run test to verify it passes**
  Run: `python tests/test_standards_engine.py`
  Expected: PASS.
- [ ] **Step 5: Commit changes**
  `git commit -m "feat(standards-engineer): add standards compliance and drift checker"`

---

### Task 4: Standards-Driven Spec Auto-Scaffolding (`shape_spec.py`)

**Files:**
- Modify: `.agents/skills/repo-standards-engineer/scripts/shape_spec.py`
- Test: `tests/test_standards_engine.py`

**Interfaces:**
- `shape_spec(root: Path, ..., from_standards: bool = False, require_envelope: bool = False)`:
  - If `from_standards` is True, queries `discover_standards(root)` and automatically injects:
    - Envelope criteria in `SPEC.md`.
    - `file_contains` or `ast_symbol_present` assertions in `VERIFICATION.json`.
    - Standards compliance assertion in `VERIFICATION.json` (`python scripts/check_compliance.py --files ...`).

- [ ] **Step 1: Write failing test for standards-driven spec shaping**
  In `tests/test_standards_engine.py`, add `test_shape_spec_from_standards()`:
  Verify that passing `--from-standards` automatically binds discovered envelope rules and compliance checks into the generated spec.
- [ ] **Step 2: Run test to verify it fails**
  Run: `python tests/test_standards_engine.py`
  Expected: FAIL on missing flag.
- [ ] **Step 3: Implement `--from-standards` in `shape_spec.py`**
  - Read cached or fresh standards.
  - Append envelope and error handling criteria to `SPEC.md`.
  - Auto-generate semantic verification contract assertions in `VERIFICATION.json`.
- [ ] **Step 4: Run test to verify it passes**
  Run: `python tests/test_standards_engine.py`
  Expected: PASS.
- [ ] **Step 5: Commit changes**
  `git commit -m "feat(standards-engineer): add --from-standards auto-wiring in shape_spec"`

---

### Task 5: Interactive Symbol Query & Reverse Indexing (`index_standards.py`)

**Files:**
- Modify: `.agents/skills/repo-standards-engineer/scripts/index_standards.py`
- Test: `tests/test_standards_engine.py`

**Interfaces:**
- `find_symbol_definition(index: dict, symbol_name: str) -> list[dict]`:
  - Returns file, line, kind, and usage occurrences.
- CLI:
  - `python scripts/index_standards.py --query <symbol>`
  - `python scripts/index_standards.py --error-code <code_name>`

- [ ] **Step 1: Write failing test for symbol querying in `index_standards.py`**
  In `tests/test_standards_engine.py`, add `test_index_standards_symbol_query()`:
  Verify querying for an error code or function returns the defining file and line.
- [ ] **Step 2: Run test to verify it fails**
  Run: `python tests/test_standards_engine.py`
  Expected: FAIL.
- [ ] **Step 3: Implement symbol search & reverse indexing in `index_standards.py`**
  - Map symbol definitions and usages.
  - Add `--query` and `--error-code` CLI flags with formatted terminal tables.
- [ ] **Step 4: Run test to verify it passes**
  Run: `python tests/test_standards_engine.py`
  Expected: PASS.
- [ ] **Step 5: Commit changes**
  `git commit -m "feat(standards-engineer): add symbol querying and reverse indexing"`

---

### Task 6: Skill Specification Sync, Pressure Tests & CI Parity Gate

**Files:**
- Modify: `.agents/skills/repo-standards-engineer/SKILL.md`
- Create: `tests/test_standards_engine_pressure.py`
- Sync: `.claude/skills/`, `.gemini/skills/`, `.opencode/skills/` via `install.ps1 -Force`

- [ ] **Step 1: Write comprehensive pressure test suite (`tests/test_standards_engine_pressure.py`)**
  Cover:
  - Large polyglot repository (100+ files with Python, TypeScript, SQL).
  - Malformed syntax handling without crashes.
  - UTF-8 Windows encoding resilience.
  - Deterministic exit codes across rich assertions.
- [ ] **Step 2: Update `SKILL.md` documentation**
  - Document all new commands (`check_compliance.py`, `--from-standards`, `--query`, rich contract assertions).
  - Add executable verification examples.
- [ ] **Step 3: Synchronize adapters and host ecosystems**
  Run:
  - `python scripts/compile_adapters.py`
  - `powershell -File install.ps1 -Skill repo-standards-engineer -Force`
  - `python scripts/validate.py` (0 errors, 0 warnings).
- [ ] **Step 4: Run all unit and pressure test suites**
  Run:
  - `python -m unittest tests/test_standards_engine_pressure.py -v`
  - `python tests/test_standards_engine.py`
  - `python scripts/release_sync.py --check`
- [ ] **Step 5: Commit changes**
  `git commit -m "feat(standards-engineer): update skill spec, add pressure test suite, and synchronize host installs"`

---

## 5. Verification Gate & Checklists

### Pre-Implementation Checklist
- [x] Read all referenced source files in `.agents/skills/repo-standards-engineer/`.
- [x] Confirmed zero third-party dependencies (100% Python standard library).
- [x] Confirmed UTF-8 console stream safety for Windows.
- [x] Confirmed adherence to single H1 and canonical markdown formatting.

### Post-Implementation Verification Matrix
| Target | Command | Success Criteria |
| :--- | :--- | :--- |
| Standards Discovery | `python scripts/discover_standards.py --json` | Detects Pydantic, TS enums, TypedDict, exit code 0 |
| Verification Contract | `python scripts/verify_spec.py --spec <dir>` | Validates file_contains, json_matches, ast_symbols, exit code 0/1 |
| Compliance Checker | `python scripts/check_compliance.py --files ...` | Flags violations, passes clean files, exit code 0/1 |
| Unit Test Suite | `python tests/test_standards_engine.py` | All unit tests PASS |
| Pressure Test Suite | `python -m unittest tests/test_standards_engine_pressure.py -v` | All pressure scenarios PASS |
| Skill Validation Gate | `python scripts/validate.py` | 24/24 PASS (0 errors, 0 warnings) |
| Release Drift Gate | `python scripts/release_sync.py --check` | Exit code 0 (no drift) |

---

## 6. Multi-Skill Upgrade Roadmap & Next Steps

This implementation plan for `repo-standards-engineer` represents **Phase 1** of our overarching canonical skill modernization roadmap. All skills authoring and maintenance in this repository adhere to the same rigorous engineering lifecycle:
$$\text{Research} \longrightarrow \text{Audit \& Review} \longrightarrow \text{Architecture Spec} \longrightarrow \text{Subagent-Driven TDD} \longrightarrow \text{Pressure Testing} \longrightarrow \text{CI Release}$$

### The 4-Skill Upgrade Sequence

| Phase | Skill Name | Current Status | Key Modernization Focus | Trigger / Handoff |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | **`repo-standards-engineer`** | 🔄 **Active (This Plan)** | Multi-paradigm AST discovery (Pydantic/TS), rich verification contracts (`file_contains`, `json_matches`), compliance drift auditor (`check_compliance.py`), and `--from-standards` spec auto-wiring. | **Current Workstream (WS-021)** |
| **Phase 2** | **`repo-blast-radius-sync`** | ⏳ **Next in Queue** | Multi-language cross-file dependency graph resolution, git diff hunk blast-radius tracking, orphaned caller & test detection, and staged parity enforcement. | Immediately upon completing Phase 1 |
| **Phase 3** | **`release-sync`** | ⏳ **Queued (3rd)** | Automated release note drafting from conventional commits, automated GitHub PR description syncing, atomic multi-registry semver gate hardening, and hook hygiene. | Immediately upon completing Phase 2 |
| **Phase 4** | **`skill-creator`** | ⏳ **Queued (4th)** | Automated pressure test suite scaffolding (`tests/test_<skill>_pressure.py`), host ecosystem compatibility matrix checker, and formal evals test harness generation. | Immediately upon completing Phase 3 |

> [!IMPORTANT]
> **Scope Invariant**: Only canonical skills authored in this repository (`.agents/skills/`) are in scope for this modernization initiative. External or third-party skills in `~/.gemini/skills/` remain untracked.

### Immediate Next Step
Upon final user approval of this updated plan, we immediately initiate execution of **Task 1 through Task 6** using **Subagent-Driven Development (SDD)** on an isolated feature branch: `feat/repo-standards-engineer-upgrade`.

