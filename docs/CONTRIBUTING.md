# Contributing

## Naming

- Lowercase with hyphens only: `my-skill-name`
- Letters, numbers, hyphens only
- Verb-first for techniques: `creating-skills`

## Description rules

- Start with `Use when...`
- Third person, triggers only, no workflow summary
- Under 500 chars, under 1024 chars frontmatter total
- Include symptoms, errors, tools for search

## Example

```yaml
---
name: condition-based-waiting
description: Use when tests have race conditions, timing dependencies, or pass/fail inconsistently
---
```

## Rules

- No `@`-links, use skill names only
- One excellent example, no multi-language dilution
- Bullets over paragraphs, ASCII only
- No TBD or TODO in docs

## Validate

- `python scripts/validate.py`
- Fix all errors before PR
- See `docs/WORKFLOW.md` for RED-GREEN-REFACTOR gate
