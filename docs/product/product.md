# Product Overview — synthesize-skills

Workspace and developer tooling for authoring, testing, validating, and installing high-reliability, reusable AI-agent skills across modern agent ecosystems.

---

## 🎯 Value Proposition & Core Purpose
- Author agent skills following standard specification conventions (YAML frontmatter, deterministic execution contracts, runnable code fences).
- Enforce strict validation rules (0-warning gate, frontmatter length bounding, code fences, trigger phrasing).
- Distribute skills seamlessly across 8 target host agent environments with atomic locking, SHA-256 idempotency, and clean rollback.
- Prevent regression and drift via automated static analysis and atomic version sync.

---

## 📦 Canonical Skills Catalog (`.agents/skills/`)

### 1. `gemini-context-engineer`
- **Purpose**: Creates, audits, and maintains workspace context files (`GEMINI.md`).
- **Features**:
  - AST-driven polyglot repository indexer and deep module leverage analyzer.
  - Subgraph dependency extractor and token-budgeted JIT context compiler.
  - VCS daemon for pre-commit signature drift detection and auto-patching.
  - Deterministic workstream verification and status transitions.

### 2. `release-sync`
- **Purpose**: Prevents version drift across project metadata and executes atomic semver bumps.
- **Features**:
  - Dual-mode gate: read-only drift verification (`--check`) and atomic bump (`--bump major|minor|patch --apply`).
  - Atomic multi-file update across `VERSION`, `GEMINI.md`, `package.json`, `README.md`, and `CHANGELOG.md` with automatic binary rollback.
  - Git worktree-aware hook installer.

### 3. `repo-blast-radius-sync`
- **Purpose**: Calculates blast radius and dependency ripple effects across repository modifications.
- **Features**:
  - Dependency registry generator and query tool (`blast_radius.py`).
  - Git diff integration supporting rename tracking and staged changes.
  - Strict parity gate (`verify_parity.py`) enforcing registry synchronization with source files.

### 4. `repo-standards-engineer`
- **Purpose**: Discovers repository standards via AST, bounds token injection, shapes interactive specs, and verifies contracts.
- **Features**:
  - Polyglot AST discovery (`discover_standards.py`) with content-addressed SHA-256 caching.
  - Maximum Information Preserving (MIP) token bounding ($\le 600$ tokens).
  - Spec Shaper (`shape_spec.py`) producing structured specs with acceptance criteria.
  - Executable Verification Engine (`verify_spec.py`) validating deterministic assertion suites.

### 5. `skill-creator`
- **Purpose**: Scaffolds, standardizes, and authors new reusable AI-agent skills.
- **Features**:
  - Stdlib-only CLI scaffolding utility (`scripts/init_skill.py`) generating specification-compliant skills.
  - Enforces strict kebab-case naming regex and frontmatter trigger structure (`Use when...`).
  - Zero-warning baseline out-of-the-box passing `scripts/validate.py`.
  - Multi-host compilation compatibility across all 8 supported agent ecosystems.

---

## 🚀 Installation & Multi-Host Adapters
- **Target Host Environments**:
  1. Open Agents Standard (`.agents/skills`)
  2. Antigravity / Gemini CLI (`.gemini/skills`, `.gemini/rules`)
  3. Claude Code (`.claude/skills`, `.claude/commands`)
  4. OpenAI Codex (`.codex/skills`, `.codex/instructions`)
  5. OpenCode (`.opencode/skills`, `.opencode/commands`)
  6. Cursor (`.cursor/skills`, `.cursor/rules/*.mdc`)
  7. Windsurf (`.windsurf/skills`, `.windsurf/rules`)
  8. GitHub Copilot (`.copilot/skills`)
- **Installers**:
  - `install.ps1`: Pure PowerShell native installer with lock files, staging buffers, `.bak` backups, and `-Rollback`.
  - `install.sh`: Pure POSIX shell installer with identical safety semantics and rollback.
- **Compilers**:
  - `scripts/manifest.py`: Maps canonical skills to host install targets.
  - `scripts/compile_adapters.py`: Transpiles skills into native host prompt commands, markdown rules, and instructions.
