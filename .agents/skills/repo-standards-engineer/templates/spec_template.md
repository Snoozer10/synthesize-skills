# Specification Template: [Feature Title]

- **Slug:** `[kebab-case-slug]`
- **Date:** [YYYY-MM-DD]
- **Status:** Draft | Active | Verified

## 1. Problem Statement
Describe the exact user problem or requirement being addressed.

## 2. Proposed Architecture & Solution
Explain key design choices, invariants, data models, and flow.

## 3. Acceptance Criteria Checklist
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## 4. Deterministic Verification Assertions
Automated assertion definitions stored in `VERIFICATION.json`.
Evidence-based completion: code is complete ONLY when `python scripts/verify_spec.py --spec specs/[slug]` exits 0.
