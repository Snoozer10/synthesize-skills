# AST Pattern Reference Guide

## Python AST Patterns
- `ast.ClassDef`: Checked for base classes containing `Enum` or class names containing `Error`/`Code`.
- `ast.Assign` & `ast.AnnAssign`: Scanned for uppercase constants representing error identifiers.
- `ast.Return`: Checked for dictionary literals containing envelope keys (`status`, `data`, `error`, `meta`).
- `ast.Call`: Checked for database driver invocations (`execute`, `query`, `raw_query`, `select`, `fetch`).

## Regex Fallback Patterns
- Error codes: `\b(ERR_[A-Z0-9_]+)\b`
- Status tokens: `status: "success"` / `status: "error"`
- Database tokens: `execute\(|query\(|select\b`
