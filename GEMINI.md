---
project_name: "synthesize-skills"
version: "1.2.0"
tech_stack:
  - "python"
  - "powershell"
  - "bash"
  - "github-actions"
rules:
  - "stdlib-only"
  - "skill-naming-convention"
  - "frontmatter-validation"
  - "read-only-research-zones"
  - "canonical-skills-source"
  - "description-starts-with-use-when"
exclude_paths:
  - ".git"
  - "__pycache__"
  - ".venv"
  - "node_modules"
  - "*.bak"
  - "Research and docs"
  - "The Created Skills"
last_indexed: "2026-09-24"
generator: "gemini-context-engineer/v4.0.0"
---

# Project Context: synthesize-skills

## 🎯 Project Overview
Workspace for authoring, validating, and installing reusable AI-agent skills. Skills are SKILL.md files with YAML frontmatter, validated by `scripts/validate.py`, and installed across 8 host directories (`.agents`, `.claude`, `.opencode`, `.gemini`, `.codex`, `.cursor`, `.windsurf`, `.copilot`). RED-GREEN-REFACTOR workflow enforces one skill at a time with pressure-scenario testing before acceptance.

## 🏗️ Architecture & Component Mapping
```
synthesize-skills/
├── .agents/skills/       # canonical skills (SSOT)
├── templates/            # SKILL.md starter template
├── scripts/              # validate.py, manifest.py, compile_adapters.py, discover/inject/shape/verify
├── tests/                # pressure scenarios and fixtures
├── docs/                 # WORKFLOW.md, CONTRIBUTING.md
├── .github/workflows/    # validate.yml CI pipeline
├── Research and docs/    # upstream research (READ-ONLY)
├── The Created Skills/   # staging area (READ-ONLY)
├── install.ps1           # Windows installer (PowerShell native, locking, rollback)
└── install.sh            # POSIX installer (pure shell, locking, rollback)
```

| Component | Path | Role |
| :--- | :--- | :--- |
| Canonical Skills | `.agents/skills/` | Single source of truth for all installed skills |
| Starter Template | `templates/skill-template/SKILL.md` | Skeleton for new skills (frontmatter + body) |
| Validator | `scripts/validate.py` | Enforces naming, frontmatter, body structure per skill |
| Manifest Generator | `scripts/manifest.py` | Maps skill -> host install paths across 8 host ecosystems |
| Adapter Compiler | `scripts/compile_adapters.py` | Compiles native adapter commands, rules, and instructions |
| Standards Engine | `scripts/discover_standards.py` | AST and pattern discovery, SHA-256 caching, token-bounded JIT injection |
| Spec Engine | `scripts/shape_spec.py` / `verify_spec.py` | Spec Shaper and deterministic executable verification contracts |
| Skill Scaffolder | `scripts/init_skill.py` | CLI scaffolding generating spec-compliant skills with kebab-case validation |
| Pressure Tests | `tests/` | Scenario fixtures verifying skill behavior under edge cases |
| Isolation Suite | `tests/test_skill_isolation_and_portability.py` | Verifies selective installation, hook chaining, and standalone execution |
| Workflow Guide | `docs/WORKFLOW.md` | RED-GREEN-REFACTOR gate with stop-gate rules |
| Contributing Guide | `docs/CONTRIBUTING.md` | Naming, description, and validation rules |
| CI Pipeline | `.github/workflows/validate.yml` | Runs `scripts/validate.py` on push/PR (Windows + Ubuntu) |
| Windows Installer | `install.ps1` | Copies skills to host dirs with selective -Skill filtering, SHA256 compare, backup, lock, rollback |
| POSIX Installer | `install.sh` | Same as above for POSIX systems with --skill filtering |

### Domain Lexicon & Ubiquitous Language
| Term | Canonical Meaning | Forbidden Synonyms / Overloaded Usage |
| :--- | :--- | :--- |
| `Skill` | A SKILL.md file with YAML frontmatter (`name`, `description`) and body providing agent instructions | "Plugin", "Extension", "Module" |
| `Canonical Skill` | Skill in `.agents/skills/` (single source of truth) | "Installed skill", "Source skill" |
| `Host Directory` | Target dir where skills are installed (`.agents/skills`, `.claude/skills`, etc.) | "Target path", "Destination" |
| `Pressure Scenario` | Test fixture verifying skill behavior under edge cases or adversarial input | "Unit test", "Integration test" |
| `Frontmatter` | YAML block between `---` fences at top of SKILL.md containing `name` and `description` | "Metadata", "Header", "Config block" |

### Architectural Health & Deep Modules
| Module / Subtree | Interface Count | Implementation LOC | Leverage | Classification |
| :--- | :--- | :--- | :--- | :--- |
| `scripts/validate.py` | 8 | 94 | 11.75 | Deep Module |

### Child Context Index
| Subtree / Scope | Context Path | Ownership & Purpose |
| :--- | :--- | :--- |
| `.agents/skills/gemini-context-engineer/` | `.agents/skills/gemini-context-engineer/GEMINI.md` | GEMINI.md creation, sync, validation, JIT compilation, VCS daemon |

## 🛑 Mandatory Engineering Constraints
1. **Stdlib-Only Scripts**: All scripts in `scripts/` MUST use Python standard library only. NEVER install or import third-party packages.
2. **Skill Naming**: Skill directory names MUST match `^[a-z0-9]+(-[a-z0-9]+)*$`. Directory name MUST equal frontmatter `name` field.
3. **Frontmatter Required**: Every SKILL.md MUST have YAML frontmatter with `name` (1-500 char description). Body MUST contain at least one runnable code fence.
4. **Description Starts With "Use when"**: Frontmatter `description` MUST begin with "Use when" to enable agent discovery.
5. **Read-Only Zones**: NEVER modify files under `Research and docs/` or `The Created Skills/` without explicit user request.
6. **Canonical Source**: `.agents/skills/` is the single source of truth. Install scripts are delivery consumers, not sources.
7. **Validate Before Commit**: Every skill MUST pass `python scripts/validate.py` before commit or PR.
8. **RED-GREEN-REFACTOR Gate**: Never batch-create skills. One skill at a time: pressure test first (RED), minimal skill second (GREEN), close loopholes third (REFACTOR).

## 🛠️ Common Workflows & CLI Commands
```bash
# Validate all skills (required before commit)
python scripts/validate.py

# Validate a specific skill
python scripts/validate.py .agents/skills/my-skill

# Generate install manifest
python scripts/manifest.py

# Dry-run install (shows what would be copied)
install.ps1                    # Windows
bash install.sh                # POSIX

# Apply install (copies to .agents, .claude, .opencode, .gemini)
install.ps1 -Force             # Windows
bash install.sh --force        # POSIX

# Selective skill install
install.ps1 -Skill skill-creator -Force
bash install.sh --skill skill-creator --force
install.ps1 -Skill "release-sync,repo-blast-radius-sync" -Force
bash install.sh --skill "release-sync,repo-blast-radius-sync" --force
```

### CI Pipeline
- Trigger: push/PR touching `.agents/skills/**`, `templates/**`, or `scripts/**`
- Matrix: `windows-latest` + `ubuntu-latest`, Python 3.11
- Gate: `python scripts/validate.py` must exit 0

### RED-GREEN-REFACTOR Workflow
1. **RED**: Write 1-3 pressure scenarios in `tests/`. Run without skill. Record exact failure.
2. **GREEN**: Write smallest SKILL.md that fixes baseline failure. Re-run scenarios. Pass = agent complies.
3. **REFACTOR**: Add explicit counters and red-flags for new rationalizations. Re-verify. Keep token cost flat.

## 🔄 Active Workstreams & Verification Status
| ID | Workstream Slice | Status | Blocked By | Proof Command |
| :--- | :--- | :--- | :--- | :--- |
| - | *No active workstreams* | - | - | - |

### Known Failure Modes & Project Learnings
- [LEARNING-001]: NEVER assume `validate.py` covers frontmatter edge cases without running it; ALWAYS execute `python scripts/validate.py` against the target skill before claiming PASS.
- [LEARNING-002]: NEVER assume empty contracts (`assertions: []` or missing `VERIFICATION.json`) pass verification legitimately; `verify_spec.py` enforces total assertions > 0 unless `--allow-empty` is explicit.
- [LEARNING-003]: ALWAYS reconfigure `sys.stdout` and `sys.stderr` to UTF-8 on Windows CLI tools to prevent `cp1256`/`cp1252` encoding crashes on Unicode output.
- [LEARNING-004]: NEVER unconditionally overwrite `.git/hooks/pre-commit`; ALWAYS inspect existing hook content, check for command presence (idempotency), and append non-destructively.
- [LEARNING-005]: ALWAYS use non-newline character classes (`[^"\'\r\n]+`) in multiline frontmatter regexes to avoid capturing subsequent YAML content or fences on unquoted values.
