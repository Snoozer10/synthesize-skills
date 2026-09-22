# Skill pressure checklist (template)

Use per skill before shipping. Copy for each skill under test.

## RED (baseline, no skill)
- [ ] Ran 1+ pressure scenario WITHOUT the skill
- [ ] Documented exact failure/rationalization verbatim
- [ ] Confirmed test fails for the right reason (not setup error)

## GREEN (minimal skill)
- [ ] Skill addresses the specific RED failure only
- [ ] Ran same scenario WITH skill, agent complies
- [ ] No extra sections added beyond the failure

## REFACTOR (close loopholes)
- [ ] Tested 1 variation/edge case, documented result
- [ ] Removed narrative, multi-language, or generic-label bloat
- [ ] Re-ran validator: PASS with zero ERRORS
