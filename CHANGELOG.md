# Changelog

## [Unreleased]
- **CI:** Add OIDC trusted publisher release workflow (`.github/workflows/release.yml`) for dual-registry publishes on `v*` tags
- **CI:** GitHub Packages publish with provenance via `secrets.GITHUB_TOKEN` (OIDC)
- **CI:** npmjs.org publish with provenance via `secrets.NPM_TOKEN` (trusted publisher)
- **Docs:** Add `docs/error-solving/understood-errors.md` with 15+ known error patterns
- **Docs:** Add `docs/handoff.md` session handoff template
- **Docs:** Add `CONTINUITY.md` project state ledger
- **Exercises:** Add `exercises/04-release-sync/` module with drift detection and atomic bump pressure scenarios
- **Chore:** Update `GEMINI.md` to v1.0.1, `last_indexed: 2026-09-14`, add LEARNING-002 through LEARNING-005
- **Chore:** Update `README.md` with GitHub Packages badge, dual-registry install instructions, provenance note
- **Git:** Force-update tag `v1.0.0` to point to current HEAD (6abc390)

## [1.0.0] - 2026-09-09
- **Breaking:** rename package `@snoozer/creating-ai-agent-skills` → `@snoozer10/synthesize-skills`, repo `Snoozer10/synthesize-skills`
- Promote `repo-blast-radius-sync` to `.agents/skills` (4 scripts + dashboard, 72-line SKILL.md)
- Fix `verify_parity -z` NUL, `5MiB/8k` binary guard, `as_posix`, `CODE_*:`, `--dry-run`, `ERR_STALE_REGISTRY`
- Marketplace: `bin/repo-sync.js` (`repo-sync dashboard --port 8765 --open`), `files` allowlist (53), `release_sync` versions `package.json`
- CI: `validate.yml` remove `cache: pip`, add `docs/blast-radius.yml`
- Scaffold repo meta: README, docs/WORKFLOW, docs/CONTRIBUTING, .gitignore, VERSION, LICENSE
- Define RED-GREEN-REFACTOR skill workflow with stop-gate