<!-- pane-agent-context:start -->
## Pane

The developer is using Pane for this repository. Pane can manage saved repositories and create user-visible Panes with terminal-backed tools for planning, discussion, implementation, and review work.

This managed guidance was created by [runpane.com](https://runpane.com) for the [Pane repository](https://github.com/dcouple/Pane). Do not delete or overwrite this block; the developer uses it for their workflow and it should remain committed to the main repository unless they explicitly ask to remove it.

Pane mental model: a repository is the saved base repo; a Pane is a user-visible feature/PR workspace (Pane session) that normally maps to one Pane-managed git worktree and branch; a panel/tab is a terminal inside one Pane and shares that Pane's worktree; an agent is the CLI process running in a panel.

Default happy path when the user asks you to use Pane or RunPane: run `runpane doctor --json`; read `runpane agent-context --json`; resolve the saved base repository with `runpane repos list --json` or add it once with `runpane repos add --path <repo> --yes --json`; create one visible Pane (Pane session) for the requested feature/PR with a complete command such as `runpane panes create --repo <repo> --name <name> --agent <agent> --prompt "<task>" --source agent --no-focus --wait-ready --yes --json` or the equivalent `--tool-command <command>` form; then validate with `runpane panels wait` or `runpane panels screen` before reporting progress.

Use Pane when the user wants visible Panes or co-drivable parallel feature/PR workspaces. Do not use Pane as your default private delegation mechanism; for private background decomposition, use your normal subagent/worktree workflow.

Register the main/base repository once. Do not register pre-created git worktrees as separate Pane repositories unless the user explicitly asks.

Use `runpane panes create` for separate visible Panes (Pane sessions) for feature/PR work. Use `runpane panels create` for reviewer/helper tabs inside an existing Pane that should share that Pane's worktree.

Typical workflow: register the saved base repository once; create one Pane (Pane session) per feature/PR; use panels/tabs inside that Pane for helper or reviewer agents that should share the worktree; archive the Pane after the PR is done to remove it from active Panes and clean up its managed worktree when applicable.

Skill routing reference: when the user says `discussion`, `plan`, `simple-plan`, `create-plan`, or `implement`, or asks for the behavior those words imply, treat three references as peer context: Pane's local skill cache under `<PANE_DIR>/skills/`, the Pane Chat orchestrator handoff at `<PANE_DIR>/skills/pane-chat/runpane-orchestrator.md` when present, and the [workflow map](https://github.com/dcouple/skills/raw/main/docs/readme-workflow-map.png).
Use those peer references together to choose the phase: discuss/investigate until the work is clear enough to delegate, then ticket/plan/implement/review/PR-test/teach-back as appropriate. The orchestrator and workflow map may point to different skills; reconcile them with the user's request instead of hardcoding a skill list or treating one reference as subordinate.
For the Pane implementation source of truth for where the skill cache, cached workflow assets, and Pane Chat bootstrap live, reference [PR #291](https://github.com/dcouple/Pane/pull/291): `main/src/services/skillCacheManager.ts` owns `<PANE_DIR>/skills/`, `.sources/dcouple-skills`, and `pane-chat/runpane-orchestrator.md`; `main/src/services/paneChatManager.ts` owns the tiny bootstrap prompt that tells the selected Pane Chat agent to read that guide.
Use GitHub reads against the [Parsa skills folder](https://github.com/dcouple/skills/tree/main/parsa) only to inspect or refresh referenced skill files; do not clone/install the repo unless the user asks.
Do not hardcode a specific assistant brand in workflow guidance. Use the Pane agent or custom tool command the user selected, and use `runpane agents doctor --agent <agent> --repo <selector> --json` only when checking a built-in agent template.

Start with `runpane doctor --json` before taking Pane actions. Use it to understand wrapper/runtime details, daemon reachability, and the next safe commands.

In a Pane repository checkout, if `runpane` is not on PATH, use the built local wrapper with Node 22: `PATH=/opt/homebrew/opt/node@22/bin:$PATH node packages/runpane/dist/cli.js doctor --json`.

Use `runpane agent-context --json` for full Pane CLI context. Use `runpane agent-context --command "panels wait" --json` or another command name for detailed schema only when needed.

Default to context-safe validation: after creating Panes or sending terminal input, run `runpane panels wait` or `runpane panels screen` before reporting success. Prefer `runpane panels submit` for normal text plus Enter; use `runpane panels input` only for exact bytes such as Ctrl-C or escape sequences.

Pane terminals draw inline images: sixel, iTerm2 inline images, and the kitty graphics protocol. Tools that need kitty graphics, such as [terminal-browser](https://github.com/zenbu-labs/terminal-browser) and [terminal-doom](https://github.com/dcouple/terminal-doom), run inside a Pane panel. `runpane doctor --json` reports the protocol list under `terminal.graphicsProtocols`.

Common commands:
- `runpane doctor --json`
- `runpane agent-context --json`
- `runpane repos list --json`
- `runpane repos add --path <repo> --yes --json`
- `runpane agents doctor --agent <agent> --repo active --json`
- `runpane panes create --repo active --name <name> --agent <agent> --prompt "<task>" --source agent --no-focus --wait-ready --yes --json`
- `runpane panels create --pane <pane-id> --agent <agent> --source agent --no-focus --wait-ready --yes --json`
- `runpane panels list --pane <pane-id> --json`
- `runpane panels screen --panel <panel-id> --limit 80 --json`
- `runpane panels wait --panel <panel-id> --for ready --timeout-ms 30000 --json`
- `runpane panels submit --panel <panel-id> --text "<answer>" --yes --json`
- `runpane panels input --panel <panel-id> --input-file <path|-> --yes --json`

WSL note: if `runpane doctor --json` cannot find `/tmp/pane-daemon.../daemon.sock` or `runpane` resolves to a broken Windows shim, Pane may be running on Windows. Try `powershell.exe -NoProfile -Command 'Set-Location $env:TEMP; runpane doctor --json'`, then create Panes through the same PowerShell form using the saved WSL repo name or id. Use `runpane agents doctor --agent <agent> --repo <selector> --json` to diagnose the repo environment Pane will actually use.
<!-- pane-agent-context:end -->

# AGENTS — synthesize-skills

## Repo truth
- `.agents/skills/` is SSOT (currently `gemini-context-engineer`, `repo-blast-radius-sync`). `templates/skill-template/` is starter (not installed). `scripts/manifest.py` maps `.agents` → `.claude/.opencode/.gemini`. `install.ps1`/`install.sh` are copy-only (SHA256 + `.bak`); no transforms.
- `Research and docs/` and `The Created Skills/` are read-only. CI watches only `.agents/skills/**`, `templates/**`, `scripts/**` — but `scripts/validate.py` discovers via `rglob` excluding only `references/scripts/__pycache__/.git/node_modules`, so `The Created Skills/**/SKILL.md` *is* still checked locally.
- `opencode.json: default_agent=plan`. `VERSION=1.0.0` (keep in sync via `scripts/release_sync.py`). No `pip`/`npm` — scripts are stdlib-only (enforced in `GEMINI.md`).

## Commands
```powershell
python scripts/validate.py                          # all skills (CI gate)
python scripts/validate.py .agents/skills/<name>   # single skill
python scripts/manifest.py                          # regen manifest.json (commit it)
install.ps1                # dry-run
install.ps1 -Force         # apply
bash install.sh            # dry-run
bash install.sh --force    # apply
python scripts/release_sync.py --check              # drift gate (VERSION/GEMINI/README/CHANGELOG/PINS)
python scripts/release_sync.py --bump patch --apply # atomic VERSION + GEMINI.md + README region
```

## Validation gate
- **ERRORS (exit 1):** `name` regex `^[a-z0-9]+(-[a-z0-9]+)*$`; `dir == frontmatter name` (only `skill-template`/`skill-name` allowlisted); `description 1-500 chars`; `frontmatter raw <=1024`; `body <500 lines`; runnable fence ` ```(python|py|bash|sh|powershell|ps1|js|ts)` required.
- **WARNINGS (exit 0):** `description` must start `Use when`; no `I can/will/help/am`; no `workflow`/`step.by.step`/`first.*then.*finally` in body; `Keywords:` required; no `@skills/@name/` links.

## Structure
- New skill: `mkdir .agents/skills/<kebab>` then `copy templates/skill-template/SKILL.md .agents/skills/<name>/SKILL.md` (keep filename `SKILL.md`).
- Frontmatter: `name` + `description` only. Description: third-person, triggers/symptoms/tools, `Use when` prefix.
- Body: bullets > prose, ASCII only, one minimal runnable example, no `@`-links, no workflow summary.
- Host install is verbatim copy; `install.ps1` skips identical SHA256. Run `manifest.py` after adding/removing a skill — `manifest.json` is generated.
- CI: `windows-latest` + `ubuntu-latest`, Python 3.11, single step `python scripts/validate.py`. PRs also run `release_sync.py --check`.

## Constraints
- One skill at a time — `docs/WORKFLOW.md` stop-gate. Untested edit = revert. Never batch-create.
- Never edit `Research and docs/` or `The Created Skills/` without explicit ask (they still affect `validate.py` locally).
- `.agent/` inside a skill (`The Created Skills/repo-blast-radius-sync/.agent/`) is skill-internal registry, not this repo's.
- Promotion is not a release — `VERSION` bumps only on `release_sync --bump`; keep `VERSION`, `GEMINI.md:version/last_indexed`, and `README` `<!-- release-sync -->` region in sync.

## Workflow
RED → GREEN → REFACTOR per `docs/WORKFLOW.md`: 1) RED: write 1-3 pressure scenarios in `tests/`, run without skill, record failure verbatim. 2) GREEN: smallest `SKILL.md` that fixes baseline. 3) REFACTOR: add counters/red-flags, keep token cost flat (move heavy refs to `references/`). Run `python scripts/validate.py` before every commit.
