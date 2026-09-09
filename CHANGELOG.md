# Changelog

## [Unreleased]

## [1.0.0] - 2026-09-09
- **Breaking:** rename package `@snoozer/creating-ai-agent-skills` → `@snoozer10/synthesize-skills`, repo `Snoozer10/synthesize-skills`
- Promote `repo-blast-radius-sync` to `.agents/skills` (4 scripts + dashboard, 71-line SKILL.md)
- Fix `verify_parity -z` NUL, `5MiB/8k` binary guard, `as_posix`, `CODE_*:`, `--dry-run`, `ERR_STALE_REGISTRY`
- Marketplace: `bin/repo-sync.js` (`repo-sync dashboard --port 8765 --open`), `files` allowlist (53), `release_sync` versions `package.json`
- CI: `validate.yml` remove `cache: pip`, add `docs/blast-radius.yml`
- Scaffold repo meta: README, docs/WORKFLOW, docs/CONTRIBUTING, .gitignore, VERSION, LICENSE
- Define RED-GREEN-REFACTOR skill workflow with stop-gate
