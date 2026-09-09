# Workflow

RED -> GREEN -> REFACTOR per writing-skills. One skill at a time.

## RED - Baseline fail

- Write 1-3 pressure scenarios in `tests/`
- Run scenario without skill
- Record exact failure and rationalization verbatim
- Do not write skill yet

## GREEN - Minimal skill

- Write smallest `SKILL.md` that fixes baseline failure
- Required frontmatter: `name`, `description`
- Keep under 500 words, bullets over prose
- Re-run same scenarios with skill
- Pass = agent complies

## REFACTOR - Close loopholes

- List new rationalizations from GREEN runs
- Add explicit counters, red-flags list
- Re-verify until no bypass
- Keep token cost flat, move heavy refs to separate files

## Stop-gate

- No next skill before current skill is verified
- No batch creation without per-skill test
- Untested edit = revert, start over

## Checks

- `python scripts/validate.py` must pass
- No `@`-links to other skills, use names only
- One example max, runnable and minimal
