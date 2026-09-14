This repository operates under an autonomous, zero-cost multi-agent software engineering swarm powered by OpenCode Zen free-tier models. All agent sessions, subagent invocations, tool operations, and state transitions must strictly adhere to the policies, permissions, and guardrails defined in this document.

---

## 1. CORE ARCHITECTURAL PHILOSOPHY: SINGLE-COMMANDER AUTONOMY

1. **The Pure Orchestrator Paradigm (Zero-Tab Architecture):**
   - The primary conversational entry point for this repository is **`orchestrator`** (`@orchestrator`), powered by the S-Tier **NVIDIA Nemotron 3 Ultra 550B LatentMoE** engine.
   - Developers do not need to manually toggle between `PLAN` and `BUILD` modes using the `Tab` key.
   - The Orchestrator operates as a **100% read-only conductor** (`edit: false, write: false, bash: whitelisted for git/baseline checks only`). It never mutates application code directly; it conducts specialized subagents end-to-end:
     $$\text{@orchestrator} \longrightarrow \text{@plan} \longrightarrow \text{@explorer} \longrightarrow \text{@private-builder} \longrightarrow \text{@architect} \longrightarrow \text{@auditor}$$

2. **Subagent Delegation Tree (`subagent_depth: 3`):**
   - Subagents are defined in `.opencode/agents/*.md` and summoned dynamically via `@<name>`.
   - Subagents execute within isolated context windows. Context bloat (raw diffs, terminal outputs, symbol listings) remains trapped inside subagents, keeping the Orchestrator's top-level reasoning sharp across long sessions.

---

## 2. THE PRIVACY FIREWALL DOCTRINE (NON-NEGOTIABLE)

```
                        DATA GOVERNANCE BOUNDARY
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         ▼                                                   ▼
🟢 GREEN ZONE (Zero Harvesting)                     🔴 RED ZONE (Quarantined)
Models: Nemotron 3 Ultra, MiMo V2.5,                Model: Muse Spark 1.3 Contributor
        Nemotron 3.5 Lightning, Ling 3.0            ─────────────────────────────────────
────────────────────────────────────                • Trains on prompt and code data.
• Enterprise-safe, open-weights.                    • BARRED from .env and credentials.
• Approved for proprietary IP, business             • BARRED from proprietary IP.
  logic, auth flows, and databases.                 • Terminal execution (bash) disabled.
```

### A. Meta Contributor Quarantine Policy
- **The Data Logging Risk:** `opencode/muse-spark-1.3-free` and `opencode/muse-spark-1.2-free` operate under Meta's Contributor license. Prompts, source files, and terminal context sent to these endpoints are retained for model training.
- **Zero-Trust Rule:** `@sandboxed-builder` (`muse-spark-1.3-free`) is **permanently barred** from accessing, reading, generating, or processing:
  1. `.env`, `.env.*`, `credentials.json`, `id_rsa`, or any secret key files.
  2. Database connection strings, API tokens, JWT secrets, or encryption keys.
  3. Proprietary algorithms, private financial records, or confidential business schemas.
- **Terminal Execution Locked:** Terminal access (`bash`) is disabled for the sandbox builder (`bash: false`) to prevent upward root directory scanning (`/` or `~`).
- **Permitted Scope:** `@sandboxed-builder` is restricted strictly to non-sensitive boilerplate, public open-source refactoring, or isolated test fixtures.

### B. Default Safe Coder
- All proprietary code, core business logic, internal database models, and production APIs must be routed exclusively to **`@private-builder` (Xiaomi MiMo V2.5 Pro Free)**, which enforces open-weights privacy and zero data harvesting.

---

## 3. THE SPEC-FIRST MANDATE ("NO SPEC, NO CODE")

1. **Hard Execution Gate:** Builders (`@private-builder` and `@sandboxed-builder`) are **mechanically locked** from editing or creating code files unless an approved, contractual specification exists in `.opencode/SPEC.md`.
2. **Interception Protocol:** If a user or automated prompt directs a builder to implement changes without an existing spec, execution must halt immediately:
   > *"Execution Halted: No approved specification found in `.opencode/SPEC.md`. Delegating to `@plan` to author requirements first."*

---

## 4. MASTER SUBAGENT DIRECTORY (`.opencode/agents/`)

| Agent Handle | Engine Slug | Mode | Tool Access (`edit` / `write` / `bash`) | Primary Operational Responsibility |
| :--- | :--- | :---: | :---: | :--- |
| **`@orchestrator`** | `nemotron-3-ultra-free` | **`primary`** | `deny` / `deny` / `whitelisted` | Swarm Commander. Coordinates the 5-phase lifecycle end-to-end. |
| **`@plan`** | `nemotron-3-ultra-free` | `subagent` | `allow` / `allow` / `deny` | Spec Author. Interrogates requirements and writes `.opencode/SPEC.md`. |
| **`@explorer`** | `nemotron-3.5-lightning-free` | `subagent` | `deny` / `deny` / `deny` *(+grep/glob)* | Recon Scout (~670 tok/s). Fast AST crawling. Populates `SCRATCHPAD.md`. |
| **`@private-builder`**| `mimo-v2.5-free` | `subagent` | `allow` / `allow` / `allow` | Default Private Coder (78.9% SWE-bench). Implements code and runs tests. |
| **`@sandboxed-builder`**|`muse-spark-1.3-free` | `subagent` | `allow` / `allow` / `deny` | Quarantined Scaffolder (943K limit). High-volume open boilerplate. |
| **`@architect`** | `nemotron-3-ultra-free` | `subagent` | `deny` / `deny` / `deny` | Debug Consultant. Root-cause diagnosis when builder tests fail $\ge 2$ times. |
| **`@auditor`** | `ling-3.0-flash-fin-free` | `subagent` | `deny` / `deny` / `deny` | Security Gatekeeper (100/100 Logic). Inspects diffs in `DIFF_GATE.md`. |

*HARD MODEL BLACKLIST:* `opencode/big-pickle` (loop crash #26220) and `opencode/muse-spark-1.2-free` (severe context cliff) are PERMANENTLY BANNED from execution.

---

## 5. STATE LEDGERS & CONTINUITY PROTOCOL

Project state is externalized into dedicated Markdown ledgers to prevent conversational context drift and token exhaustion:

### A. The 3-File Swarm State Ledger (`.opencode/`)
1. **`.opencode/SPEC.md` [IMMUTABLE]:**
   - Authored by `@plan`.
   - Contains executive summary, in/out of scope declarations, target file maps, atomic implementation steps, and acceptance test commands.
2. **`.opencode/SCRATCHPAD.md` [EPHEMERAL]:**
   - Populated by `@explorer`.
   - Contains raw line citations, symbol signatures, and dependency trees.
   - Automatically excluded from git (`.git/info/exclude`). Cleared after task completion.
3. **`.opencode/DIFF_GATE.md` [STAGING]:**
   - Populated by builders (`@private-builder` / `@sandboxed-builder`).
   - Contains unified AST diffs, local terminal test outputs, and lint proofs awaiting review by `@auditor`.

### B. Long-Term Developer Continuity & Pedagogy (`CONTINUITY.md` & `drills/`)
If `CONTINUITY_POLICY: AUTO` or `SCAFFOLD` is enabled:
- **`docs/CONTINUITY.md` (or `CONTINUITY.md`):** Updated upon every successful task completion. Moves the active task to **Done** with test verification evidence, sets the next item to **Now**, and preserves historical architectural decisions.
- **Pedagogical Knowledge Capture (`exercises/` or `drills/`):** When complex bugs or architectural patterns are resolved, `@orchestrator` scaffolds a drill artifact detailing:
  1. Problem Diagnosed
  2. Solution & Invariants Preserved
  3. Verification & Proof Command

---

## 6. THE 5-STAGE AUTONOMOUS EXECUTION PIPELINE

```
[USER GOAL]
     │
     ▼
[STAGE 0: PRE-FLIGHT BASELINE] ───► git status & baseline tests (Exit code 0 check)
     │
     ▼
[STAGE 1: SPECIFICATION] ────────► @plan drafts .opencode/SPEC.md
     │
     ▼
[STAGE 2: RECONNAISSANCE] ────────► @explorer maps symbols to SCRATCHPAD.md (~670 tok/s)
     │
     ▼
[STAGE 3: IMPLEMENTATION] ────────► @private-builder implements AST diffs & runs tests
     │                                     │
     │ (If tests fail 2x)                  ▼
     ├──────────────────────────────► @architect diagnoses root cause
     │
     ▼
[STAGE 4: SECURITY AUDIT] ────────► @auditor inspects DIFF_GATE.md
     │                                     │
     │ (If REJECTED)                       ▼
     └──────────────────────────────► Builder remediates specific line citations
     │ (If APPROVED)
     ▼
[STAGE 5: REPORT & COMMIT] ───────► Atomic git commit staged to <TargetFiles>
```

### Stage Execution Rules:
1. **Pre-Flight Baseline:** Check `git status --porcelain`. Never build features on top of a dirty working tree or failing baseline test suite.
2. **Surgical Diffs (Anti-Scope Creep):** Builders must modify ONLY files declared in `.opencode/SPEC.md`. Cosmetic reformatting or reordering of untouched lines is strictly forbidden.
3. **Falsifiable Verification Only:** Qualitative statements ("code looks good") are REJECTED. All tasks must be verified by automated terminal commands returning exit code `0`.
4. **Mandatory Gatekeeper Audit:** A task CANNOT be committed to Git without an explicit `[VERDICT: APPROVED]` from `@auditor` confirming OWASP security, logic correctness, and zero secret leaks.
5. **Circuit Breaker (`MAX_TASK_RETRIES = 2`):** If a builder fails local tests across two consecutive turns, it must stop editing and invoke `@architect`. If debugging fails, the **Dual Rollback Protocol** is triggered:
   - Tracked files: `git restore <file>`
   - Untracked files: `rm -f <file>`

---

## 7. GIT SAFETY & ATOMIC COMMIT RULES

- **NEVER** run destructive commands (`git reset --hard`, `git clean -fd`, `git checkout -f`).
- **NEVER** run blanket staging commands (`git add .` or `git add -A`).
- **ALWAYS** stage declared target files explicitly:
  ```bash
  git add <TargetFiles>
  git commit -m "<type>(<scope>): <concise description matching SPEC.md>"
  ```
- If continuity files were updated:
  ```bash
  git add <CONTINUITY_TARGET> <PEDAGOGY_TARGET>
  git commit -m "docs(continuity): sync ledger and drill for <task-id>"
  ```

---

## 8. TOKEN HYGIENE & COMPACTION TRIPWIRES

To prevent reasoning degradation and context cliff collapse over long sessions:
- **15-Turn Session Tripwire:** If an active session reaches **15 interaction turns**, complete the active atomic task, commit verified changes, sync `.opencode/SPEC.md`, and instruct the user to run `/compact` or launch a fresh session.
- **Model Compaction Ceilings:**
  - `nemotron-3-ultra-free` (Orchestrator/Plan): Reset or compact at **200,000 tokens**.
  - `mimo-v2.5-free` (Builder): Compact at **750,000 tokens**.
  - `muse-spark-1.3-free` (Sandbox): Compact at **800,000 tokens**.
  - `ling-3.0-flash-fin-free` (Auditor): Keep payloads under **180,000 tokens** for peak logic fidelity.

---

## 9. EMERGENCY FAILOVER PLAYBOOK

If an OpenCode Zen free model returns `HTTP 429 Too Many Requests` or experiences high latency:
- **`nemotron-3-ultra-free` throttles:** Wait 60 seconds with exponential backoff. **NEVER failover to `big-pickle`** (banned due to infinite loop bug #26220).
- **`mimo-v2.5-free` throttles:** Temporarily route coding tasks to `nemotron-3-ultra-free` (read-only architectural advice) or pause execution.
- **`muse-spark-1.3-free` throttles:** Re-route task to `@private-builder` (`mimo-v2.5-free`). **NEVER failover to `muse-spark-1.2-free`** (banned due to severe context cliff).
- **`ling-3.0-flash-fin-free` throttles:** Delegate audit verification to `@architect` (`nemotron-3-ultra-free`) with strict security prompts.

# AGENTS — synthesize-skills

## Repo truth
- `.agents/skills/` is SSOT (currently `gemini-context-engineer`, `repo-blast-radius-sync`, `release-sync`). `templates/skill-template/` is starter (not installed). `scripts/manifest.py` maps `.agents` → `.claude/.opencode/.gemini`. `install.ps1`/`install.sh` are copy-only (SHA256 + `.bak`); no transforms.
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

# Portable release-sync skill (self-contained, stdlib-only)
python .agents/skills/release-sync/scripts/check.py [--json]        # drift gate (80/20: FAIL only on version parity)
python .agents/skills/release-sync/scripts/bump.py patch [--apply] [--json]  # atomic semver bump

# Legacy root script (dogfooding this repo only)
python scripts/release_sync.py --check              # drift gate (VERSION/GEMINI/README/CHANGELOG/PINS)
python scripts/release_sync.py --bump patch --apply # atomic VERSION + GEMINI.md + README region

# npm marketplace (optional)
npx --package @snoozer10/synthesize-skills repo-sync add <skill>
npx --package @snoozer10/synthesize-skills repo-sync dashboard --port 8765 --open
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
- **release-sync is portable:** bundled `check.py` + `bump.py` in `.agents/skills/release-sync/scripts/` — copy/paste to any project, invoke, works. No dependency on root `scripts/release_sync.py`.

## Workflow
RED → GREEN → REFACTOR per `docs/WORKFLOW.md`: 1) RED: write 1-3 pressure scenarios in `tests/`, run without skill, record failure verbatim. 2) GREEN: smallest `SKILL.md` that fixes baseline. 3) REFACTOR: add counters/red-flags, keep token cost flat (move heavy refs to `references/`). Run `python scripts/validate.py` before every commit.
- New pressure test: `tests/test_release_sync_pressure.py` (2 scenarios: drift detection, dry-run bump)