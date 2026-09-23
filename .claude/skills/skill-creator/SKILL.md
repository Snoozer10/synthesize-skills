---
name: skill-creator
description: Use when authoring, scaffolding, validating, or packaging new reusable AI-agent skills across multiple agent ecosystems.
---

# skill-creator

Standardized scaffolding and authoring toolkit for cross-host AI-agent skills.

## Quickstart

Initialize a new skill with valid metadata, directory layout, and starter files:

```bash
# Scaffold a new skill in .agents/skills
python scripts/init_skill.py my-new-skill --desc "Use when performing tasks with my new skill." --keywords "tools, tasks, automation"
```

```powershell
# Windows PowerShell invocation
python scripts/init_skill.py my-new-skill --desc "Use when performing tasks with my new skill." --keywords "tools, tasks, automation"
```

## Operations

### 1. Scaffolding Structure
Running `init_skill.py` creates a directory conforming to the agentskills.io standard:
- `SKILL.md` with YAML frontmatter (`name`, `description`).
- `scripts/` directory for execution utilities.
- `references/` directory for supplementary documentation.

### 2. Validation Pre-Flight
Always validate newly scaffolded or edited skills before committing:
```bash
python scripts/validate.py .agents/skills/my-new-skill
```

### 3. Multi-Host Compilation
Once the skill passes validation, compile adapters across host directories:
```bash
python scripts/manifest.py
python scripts/compile_adapters.py
```

## Keywords
skill-creator, scaffold, authoring, agentskills, init_skill, skills-engine
