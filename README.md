# Creating AI-Agent Skills

Repo for authoring, validating, and installing reusable AI-agent skills.

- Canonical skills live in `.agents/skills/<name>/SKILL.md`
- Templates, scripts, and tests enforce structure before install

## Layout

- `.agents/skills/` - canonical installed skills, one dir per skill
- `templates/` - SKILL.md starter template
- `scripts/` - `validate.py`, install helpers
- `tests/` - pressure scenarios and fixtures
- `docs/` - `WORKFLOW.md`, `CONTRIBUTING.md`
- `Research and docs/` - upstream research, read-only
- `The Created Skills/` - staging area, read-only

## Quickstart

- Copy template:
  - `copy templates\\SKILL.md .agents\\skills\\<my-skill>\\SKILL.md`
- Edit name and description per `docs/CONTRIBUTING.md`
- Validate:
  - `python scripts/validate.py`
- Install dry-run:
  - `install.ps1                # dry-run (Windows)`
  - `bash install.sh            # dry-run (POSIX)`
- Install:
  - `install.ps1 -Force         # apply`
  - `bash install.sh --force    # apply`

## Marketplace

Install `repo-blast-radius-sync` in any project:

```bash
npx skills add repo-blast-radius-sync
# or
ux add repo-blast-radius-sync
# or manual
git clone https://github.com/your-org/creating-ai-agent-skills
python scripts/validate.py && python scripts/manifest.py && install.ps1 -Force  # or bash install.sh --force
```

Live dashboard (human + agent):

```bash
python .agents/skills/repo-blast-radius-sync/scripts/dashboard.py --port 8765 --once --json .agent/dashboard.json
# human: open http://127.0.0.1:8765
# agent: curl http://127.0.0.1:8765/api/status  or  cat .agent/dashboard.json | python -m json.tool
python .agents/skills/repo-blast-radius-sync/scripts/dashboard.py --port 8765 --watch  # poll 2s
```

## Docs

- Workflow: `docs/WORKFLOW.md`
- Contributing: `docs/CONTRIBUTING.md`
- Changelog: `CHANGELOG.md`
<!-- release-sync:start -->
Version: 0.1.2
<!-- release-sync:end -->

