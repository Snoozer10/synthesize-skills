---
name: repo-standards-engineer
description: "Use when extracting codebase standards, response envelopes, and error codes via AST, injecting token-bounded invariants into agent context, shaping interactive specs, or executing deterministic contract verifications"
---

# repo-standards-engineer

## Overview
- AST Standards Discovery: scans repositories to extract response envelopes, error enums, and database patterns with SHA-256 caching.
- JIT Token Bounding: injects repo standards and invariants under a strict token budget (MIP <= 600 tokens).
- Spec Shaper: generates structured specifications in `specs/<slug>/` with acceptance criteria and execution boundaries.
- Contract Verifier: deterministically executes acceptance assertions before claiming completion.

## When to Use
- Before generating code in unfamiliar codebases to discover conventions and envelopes.
- Injecting standards into subagents, system prompts, or context (`@repo-standards`).
- Shaping new feature specs with interactive or scripted acceptance criteria.
- Verifying completion of tasks using executable assertion contracts.
- When NOT to use: one-line scratch edits, non-code repositories, or purely aesthetic checks.

Keywords: standards, ast, envelopes, error-codes, invariants, spec-shaper, verification, contracts, token-bounding

## Quick Reference
| Task | Command |
| :--- | :--- |
| Discover standards (JSON) | `python scripts/discover_standards.py --json` |
| Force rescan (bypass cache) | `python scripts/discover_standards.py --force` |
| Inject standards (Markdown <= 600 tokens) | `python scripts/inject_standards.py --max-tokens 600` |
| Inject compact standards | `python scripts/inject_standards.py --format compact` |
| Shape a feature spec | `python scripts/shape_spec.py --slug <slug> --title "<title>" --criterion "<text>"` |
| Interactive spec interview | `python scripts/shape_spec.py --interactive` |
| Verify spec contract | `python scripts/verify_spec.py --spec specs/<slug>` |

## Verification Example
```bash
python scripts/discover_standards.py --json
python scripts/inject_standards.py --max-tokens 600
python scripts/shape_spec.py --slug sample-task --title "Sample Task" --criterion "scripts/validate.py exists" --assert-file "scripts/validate.py"
python scripts/verify_spec.py --spec specs/sample-task
```

```python
import subprocess
import sys

res = subprocess.run([sys.executable, "scripts/discover_standards.py", "--json"], capture_output=True, text=True)
assert res.returncode == 0, f"Discovery failed: {res.stderr}"
print("PASS: standards discovered")
```

## Dual-Axis Subagent Review Pattern
When executing non-trivial feature implementations:
1. **Standards Auditor Subagent**: inspects implementation AST and verifies adherence to discovered response envelopes, naming conventions, and error code enums.
2. **Spec Auditor Subagent**: executes `python scripts/verify_spec.py --spec specs/<slug>` to confirm all deterministic acceptance criteria pass without manual hand-waving.

## Common Pitfalls
- Assuming API response structures without running discovery. Fix: run `python scripts/discover_standards.py`.
- Bloating context with multi-page standards docs. Fix: use `python scripts/inject_standards.py --max-tokens 600`.
- Claiming a task is complete without automated receipts. Fix: enforce `scripts/verify_spec.py` exit code 0.
