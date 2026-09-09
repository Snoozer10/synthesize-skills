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

# Agent Guide — Creating AI-Agent Skills

## Repo truth
- `.agents/skills/` is SSOT. `templates/skill-template/` is starter, not installed. `scripts/manifest.py` maps to hosts (`.agents`, `.claude`, `.opencode`, `.gemini`). `install.ps1`/`install.sh` are copy-only consumers with SHA256 compare + `.bak` backup.
- `Research and docs/` (upstream) and `The Created Skills/` (staging) are read-only zones. CI only watches `.agents/skills/**`, `templates/**`, `scripts/**`. Do not edit those zones without explicit user ask.
- `opencode.json` sets `default_agent: plan`. `VERSION` is `0.1.0`.

## Commands (exact, copy-paste)
```powershell
python scripts/validate.py
python scripts/validate.py .agents/skills/<name>
python scripts/manifest.py
install.ps1                # dry-run (Windows)
install.ps1 -Force         # apply
bash install.sh            # dry-run (POSIX)
bash install.sh --force    # apply
```

Release (evergreen): python scripts/release_sync.py --check # CI gate; python scripts/release_sync.py --bump patch --apply # atomic VERSION/CHANGELOG/GEMINI/README

## Validation gate (trust `scripts/validate.py`, not prose)
- Discovery: `rglob("SKILL.md")` excluding `references/`, `scripts/`, `__pycache__`, `.git`, `node_modules`. That means `templates/skill-template/SKILL.md` and `The Created Skills/**/SKILL.md` ARE checked.
- ERRORS (exit 1): `name` regex `^[a-z0-9]+(-[a-z0-9]+)*$`; `dir name == frontmatter name` (only `skill-template`/`skill-name` is allowlisted); `description 1-500 chars`; `frontmatter raw <=1024 chars`; `body <500 lines`; runnable fence ` ```(python|py|bash|sh|powershell|ps1|js|ts)` required.
- WARNINGS (exit 0): `description` must start `Use when`; no `I can/will/help/am`; no `workflow`/`step.by.step`/`first.*then.*finally` in body; `Keywords:` required; no `@skills`/`@name/` links (use skill name).
- Current PASS shows warnings only (e.g. `gemini-context-engineer` 3 warnings). Fix ERRORs only; warnings are style.

## Structure that matters
- Add/edit skill: `mkdir .agents/skills/<kebab-case-name>` then copy `templates/skill-template/SKILL.md` -> `.agents/skills/<name>/SKILL.md`. Keep file name `SKILL.md`.
- Host install: `.agents/skills/<name>/` copied verbatim to `.claude/skills/<name>/`, `.opencode/skills/<name>/`, `.gemini/skills/<name>/`. `install.ps1` skips identical SHA256.
- Scripts are stdlib-only (validated by `GEMINI.md` constraint). No `pip install`, no `npm`. CI matrix `windows-latest` + `ubuntu-latest`, Python 3.11, single step `python scripts/validate.py`.

## Constraints to not miss
- Never batch-create skills. One skill at a time per `docs/WORKFLOW.md` stop-gate. Untested edit = revert.
- Frontmatter: `name` + `description` only per template. Keep description third-person, triggers/symptoms/tools, under 500 chars, include searchable `Keywords:` in body.
- Body: one minimal runnable example, bullets over prose, ASCII only, under 500 words/lines, no `@`-links, no workflow summary.
- `.agent/` at skill level (`The Created Skills/repo-blast-radius-sync/.agent/`) is skill-internal registry, not this repo's.

## Workflow (RED -> GREEN -> REFACTOR)
1. RED: write 1-3 pressure scenarios in `tests/`, run without skill, record exact failure verbatim.
2. GREEN: smallest SKILL.md that fixes baseline, re-run scenarios, pass = agent complies.
3. REFACTOR: add counters/red-flags for new rationalizations, keep token cost flat (move heavy refs to separate files).
- Check `docs/WORKFLOW.md` + `docs/CONTRIBUTING.md` for gate details before PR. Run `python scripts/validate.py` before every commit.
