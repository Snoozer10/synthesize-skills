---
name: repo-standards-engineer
description: "Use when extracting codebase standards, response envelopes, and error codes via AST, checking architectural compliance, indexing symbols, shaping specs with rich semantic assertions, or verifying contracts in specs directory"
---

# repo-standards-engineer

## Overview
- AST Standards Discovery: `discover_standards.py` extracts response envelopes, error enums, dataclasses, Pydantic models, and database patterns with SHA-256 caching.
- Standards Compliance & Drift Checker: `check_compliance.py` audits code changes or staged diffs against Rule 1 (Error Code Governance), Rule 2 (Response Envelope Integrity), and Rule 3 (Database Query Governance).
- Symbol & Error Code Reverse Indexer: `index_standards.py` maps symbols and error codes to exact defining source files and line numbers with CLI and API query support.
- JIT Token Bounding: `inject_standards.py` injects repo standards and invariants under a strict token budget (MIP <= 600 tokens).
- Spec Shaper with Auto-Wiring: `shape_spec.py` (`--from-standards`, `--assert-file`, `--assert-contains`, `--assert-regex`, `--assert-json`, `--assert-symbol`) weaves discovered standards into specs and automated verification contracts.
- Contract Verifier: `verify_spec.py` deterministically executes acceptance assertions including rich semantic checks (`file_contains`, `regex_matches`, `json_matches`, `ast_symbol_present`) and automated commands.

## When to Use
- Discovering conventions, schemas, and response envelopes in unfamiliar polyglot codebases.
- Auditing modified or staged files against declared repository error codes and response standards.
- Reverse-querying defining source locations for specific error codes or domain symbols.
- Shaping feature specs auto-wired with repository standards and rich semantic assertions.
- Enforcing deterministic acceptance contracts before claiming task completion.
- When NOT to use: one-line scratch edits, non-code repositories, or purely aesthetic checks.

Keywords: code-standards, ast-extraction, response-envelopes, error-codes, compliance-checker, architectural-drift, symbol-index, reverse-query, rich-assertions, spec-shaper, deterministic-contracts, contract-verification

## Quick Reference
| Task | Command |
| :--- | :--- |
| Discover standards (JSON) | `python scripts/discover_standards.py --json` |
| Force rescan (bypass cache) | `python scripts/discover_standards.py --force` |
| Audit file compliance | `python scripts/check_compliance.py --files src/app.py` |
| Audit git staged diffs | `python scripts/check_compliance.py --staged` |
| Query symbol definition | `python scripts/index_standards.py --query <symbol>` |
| Query error code definition | `python scripts/index_standards.py --error-code <code_name>` |
| Inject standards (<= 600 tokens) | `python scripts/inject_standards.py --max-tokens 600` |
| Shape spec with standards | `python scripts/shape_spec.py --from-standards --slug <slug> --title "<title>" --assert-file <path>` |
| Shape spec with rich assertions | `python scripts/shape_spec.py --slug <slug> --title "<title>" --assert-symbol "file.py:class:MyClass"` |
| Verify spec contract | `python scripts/verify_spec.py --spec specs/<slug>` |

## Verification Example
```bash
python scripts/discover_standards.py --json
python scripts/check_compliance.py --files src/app.py
python scripts/index_standards.py --error-code ERR_UNAUTHORIZED
python scripts/shape_spec.py --from-standards --slug user-feature --title "User Feature" --assert-file src/app.py
python scripts/verify_spec.py --spec specs/user-feature
```

```python
import subprocess
import sys

res = subprocess.run([sys.executable, "scripts/check_compliance.py", "--files", "src/app.py"], capture_output=True, text=True)
print("Compliance check exit code:", res.returncode)
```

## Dual-Axis Subagent Review Pattern
When executing non-trivial feature implementations:
1. Standards Auditor: audits code with `check_compliance.py` to ensure zero undeclared error codes, envelope deviations, or prohibited query patterns.
2. Spec Contract Auditor: executes `verify_spec.py --spec specs/<slug>` to guarantee all file existence, semantic assertions, and command contracts pass deterministically.

## Common Pitfalls
- Assuming API response structures without running discovery. Remediation: run `python scripts/discover_standards.py`.
- Introducing undeclared error codes or rogue envelope keys. Remediation: run `python scripts/check_compliance.py`.
- Manually hunting where error codes or symbols are defined. Remediation: run `python scripts/index_standards.py --error-code <code_name>`.
- Bloating context with multi-page standards docs. Remediation: run `python scripts/inject_standards.py --max-tokens 600`.
- Claiming task completion without automated receipts. Remediation: enforce `python scripts/verify_spec.py --spec specs/<slug>`.
