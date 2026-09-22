# /release-sync
"Use when VERSION, GEMINI.md, or package.json versions may drift, when CHANGELOG/README hygiene is needed, or before bumping major|minor|patch — parity gate and atomic bump for release_sync"

## Instructions
When this command is invoked:
1. Load and read the instructions from canonical skill: `.agents/skills/release-sync/SKILL.md`
2. Follow all guidelines, contracts, and validation rules specified in that skill.
3. If arguments are passed ($ARGUMENTS), apply them as context parameters.
