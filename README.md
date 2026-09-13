# synthesize-skills

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](VERSION)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/Snoozer10/synthesize-skills/validate.yml?branch=main)](https://github.com/Snoozer10/synthesize-skills/actions/workflows/validate.yml)
[![Python](https://img.shields.io/badge/python-3.11+-yellow)](https://www.python.org/)

> Repo for authoring, validating, and installing reusable AI-agent skills.

## Skills Catalog (3 skills)

| Skill | Description | Trigger | Install |
|-------|-------------|---------|---------|
| `gemini-context-engineer` | Use when creating or maintaining GEMINI.md, mapping repository architecture, compiling task context slices, guarding git boundaries, or verifying execution contracts | GEMINI.md tasks | `repo-sync add gemini-context-engineer` |
| `repo-blast-radius-sync` | Use when modifying, refactoring, adding features, or fixing bugs in code, scripts, schemas, or configs where callers, tests, or docs must stay in sync — detects blast radius and blocks orphaned commits | Refactor/feature/bugfix | `repo-sync add repo-blast-radius-sync` |
| `release-sync` | Use when VERSION, GEMINI.md, or package.json versions may drift, when CHANGELOG/README hygiene is needed, or before bumping major\|minor\|patch — parity gate and atomic bump for release_sync | Release prep | `repo-sync add release-sync` |

## Install (From Source — Always Works)

```bash
git clone https://github.com/Snoozer10/synthesize-skills
cd synthesize-skills
python scripts/validate.py && python scripts/manifest.py
install.ps1 -Force    # Windows
bash install.sh --force  # POSIX
```

Copies all 3 skills to 4 host directories: `.agents/skills/`, `.claude/skills/`, `.opencode/skills/`, `.gemini/skills/`

## Platform Support (4 Host Targets)

| Platform | Host Directory | Install Method |
|----------|----------------|----------------|
| OpenCode | `.opencode/skills/` | `install.ps1 -Force` / `bash install.sh --force` |
| Claude Code | `.claude/skills/` | Same |
| Gemini CLI | `.gemini/skills/` | Same |
| Generic / Agents | `.agents/skills/` | Same (canonical) |

## Workflow

RED → GREEN → REFACTOR per `docs/WORKFLOW.md`:

1. **RED**: Write pressure scenarios in `tests/`, run without skill, record failure
2. **GREEN**: Write minimal `SKILL.md` that fixes baseline
3. **REFACTOR**: Add counters/red-flags, keep token cost flat

## Development Commands

```bash
python scripts/validate.py              # CI gate (required before commit)
python scripts/manifest.py              # Regen manifest.json
python scripts/release_sync.py --check  # Drift gate (dogfooding)
python scripts/release_sync.py --bump patch --apply  # Release
```

## Architecture

```
synthesize-skills/
├── .agents/skills/       # canonical skills (SSOT)
├── templates/            # SKILL.md starter template
├── scripts/              # validate.py, manifest.py, release_sync.py
├── tests/                # pressure scenarios and fixtures
├── docs/                 # WORKFLOW.md, CONTRIBUTING.md
├── .github/workflows/    # validate.yml CI pipeline
├── Research and docs/    # upstream research (READ-ONLY)
├── The Created Skills/   # staging area (READ-ONLY)
├── install.ps1           # Windows installer
└── install.sh            # POSIX installer
```

| Component | Path | Role |
| :--- | :--- | :--- |
| Canonical Skills | `.agents/skills/` | Single source of truth for all installed skills |
| Starter Template | `templates/skill-template/SKILL.md` | Skeleton for new skills (frontmatter + body) |
| Validator | `scripts/validate.py` | Enforces naming, frontmatter, body structure per skill |
| Manifest Generator | `scripts/manifest.py` | Maps skill → host install paths (`.agents`, `.claude`, `.opencode`, `.gemini`) |
| Pressure Tests | `tests/` | Scenario fixtures verifying skill behavior under edge cases |
| Workflow Guide | `docs/WORKFLOW.md` | RED-GREEN-REFACTOR gate with stop-gate rules |
| Contributing Guide | `docs/CONTRIBUTING.md` | Naming, description, and validation rules |
| CI Pipeline | `.github/workflows/validate.yml` | Runs `scripts/validate.py` on push/PR (Windows + Ubuntu) |
| Windows Installer | `install.ps1` | Copies skills to host dirs with SHA256 compare and backup |
| POSIX Installer | `install.sh` | Same as above for POSIX systems |

## Links

- Workflow: `docs/WORKFLOW.md`
- Contributing: `docs/CONTRIBUTING.md`
- Changelog: `CHANGELOG.md`
- License: `LICENSE`
<!-- release-sync:start -->
Version: 1.0.0
<!-- release-sync:end -->