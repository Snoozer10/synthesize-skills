---
name: skill-name
description: Use when creating a new reusable skill from a proven technique, pattern, or reference that future agents must discover and apply
---

# Skill Name

## Overview
One technique in 1-2 sentences. Core principle stated plainly.

## When to Use
- Symptom or trigger 1: concrete situation where this applies
- Symptom or trigger 2: error message, behavior, or request type
- When NOT to use: one-off fix, unrelated stack, or project-specific rule

Keywords: trigger, symptom, error, fallback, pattern, workflow

## Quick Reference
| Situation | Action |
|-----------|--------|
| Common case | Do X |
| Edge case | Do Y |
| Unsure | Read Implementation below |

## Implementation
Steps:

1. Identify the trigger from When to Use.
2. Apply the minimal pattern below.
3. Verify with the runnable example.

```python
def greet(name):
    if not name:
        raise ValueError("name must be non-empty")
    return "hello " + name


if __name__ == "__main__":
    assert greet("sam") == "hello sam"
    try:
        greet("")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
    print("PASS")
```

## Common Mistakes
- Mistake 1: copying the pattern without checking triggers. Fix: re-read When to Use first.
- Mistake 2: adding options for later. Fix: delete them; add when a real case needs them.
