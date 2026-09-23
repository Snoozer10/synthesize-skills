# Understood Errors — synthesize-skills

Catalog of known error patterns, causes, and resolutions encountered during development.

---

## NPM Authentication & Publishing

### ENEEDAUTH / 401 Unauthorized on npm publish
**Error:**
```
npm ERR! code ENEEDAUTH
npm ERR! need auth This command requires you to be logged in
```
**Cause:** Missing or invalid npm token in CI/CD environment.
**Resolution:**
- For npmjs.org: Configure `NPM_TOKEN` secret in GitHub Actions (automation token, not personal)
- For GitHub Packages: Use `secrets.GITHUB_TOKEN` with `id-token: write` permission
- Verify token scope: `write:packages` for GitHub, `publish` for npm

### npm EOTP — Token name is not token type
**Error:**
```
npm error code EOTP
npm error This operation requires a one-time password from your authenticator.
```
**Cause:** Three distinct root causes all produce the same EOTP error:
1. **Wrong token type**: A "Publish" or "Read-only" Classic token was stored as `NPM_TOKEN`. Only "Automation" type bypasses 2FA in CI.
2. **Token name ≠ token type**: npm token names are arbitrary labels. A token named "Automation" may still be a Publish-type token if created with publish scope.
3. **CLI creation interactive**: `npm token create --type=automation` prompts for password and authenticator OTP interactively.

**Resolution:**
- Create a **Classic Automation** token via web UI:
  1. Go to https://www.npmjs.com/settings/<user>/tokens/new
  2. Select **"Classic Token"**
  3. Select scope **"Automation"** (explicitly labeled: "bypasses two-factor authentication")
  4. Store it as `NPM_TOKEN` secret: `gh secret set NPM_TOKEN -R <owner>/<repo>`
- Verify on the Access Tokens list page that the "Bypass 2FA" column shows ✓ for your token row.
**Error:**
```
npm ERR! code E403
npm ERR! 403 You must verify your email before publishing
```
**Cause:** npm account email not verified.
**Resolution:** Verify email at https://www.npmjs.com/settings/<user>/emails

---

## Git Tag & Release Issues

### Tag points to wrong commit
**Error:** `git tag v1.0.0` points to old release commit, not current HEAD.
**Cause:** Tag created at initial release, subsequent commits not tagged.
**Resolution:**
```bash
git tag -f v1.0.0          # Force-update local tag to HEAD
git push origin v1.0.0 --force  # Force-push to remote
```

### "Tag already exists" on push
**Error:**
```
! [rejected]        v1.0.0 -> v1.0.0 (already exists)
```
**Cause:** Tag exists locally and/or remotely with different commit.
**Resolution:** Use `--force` or delete and recreate:
```bash
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
git tag v1.0.0
git push origin v1.0.0
```

---

## GitHub Actions OIDC

### "id-token: write" permission missing
**Error:**
```
Error: The request is missing the required parameter: id_token
```
**Cause:** Workflow missing `permissions: id-token: write`.
**Resolution:** Add to workflow:
```yaml
permissions:
  id-token: write
  contents: read
```

### npm trusted publisher: "Workflow file not found"
**Error:**
```
Unable to authenticate: workflow file release.yml not found
```
**Cause:** Workflow filename in npm trusted publisher config doesn't match actual file.
**Resolution:** Ensure exact match (case-sensitive, include `.yml`):
- npm config: `release.yml`
- Actual file: `.github/workflows/release.yml`

### GitHub Packages: "Package not found" / 404
**Error:**
```
npm ERR! 404 Not Found - GET https://npm.pkg.github.com/@snoozer10%2fsynthesize-skills
```
**Cause:** Package not published to GitHub Packages, or Actions access not granted.
**Resolution:**
1. Publish once manually: `npm publish --registry=https://npm.pkg.github.com`
2. Grant Actions access: Package settings → Actions access → Add repository → Write role

---

## Validation & CI

### validate.py: "Frontmatter description must start with 'Use when'"
**Error:**
```
ERROR: .agents/skills/my-skill/SKILL.md: description must start with "Use when"
```
**Cause:** Skill frontmatter description doesn't follow convention.
**Resolution:** Prefix description with "Use when " (third-person, trigger-focused).

### validate.py: "Skill directory name must match frontmatter name"
**Error:**
```
ERROR: .agents/skills/my-skill/SKILL.md: dir name 'my-skill' != frontmatter name 'my_skill'
```
**Cause:** Directory name uses kebab-case, frontmatter uses snake_case.
**Resolution:** Both must be identical kebab-case: `my-skill`.

### release_sync.py --check: "VERSION is gitignored"
**Error:**
```
drift: VERSION is gitignored (git check-ignore -q) — remove from .gitignore
```
**Cause:** `VERSION` file listed in `.gitignore`.
**Resolution:** Remove `VERSION` from `.gitignore` (must be tracked for release automation).

### release_sync.py --check: "CHANGELOG.md missing ## [Unreleased]"
**Error:**
```
drift: CHANGELOG.md missing ## [Unreleased]
```
**Cause:** CHANGELOG.md doesn't have the required unreleased section header.
**Resolution:** Ensure CHANGELOG.md starts with:
```markdown
# Changelog

## [Unreleased]

## [1.0.0] - 2026-09-09
...
```

---

## Installer Scripts

### install.ps1: "SHA256 mismatch" on identical files
**Error:**
```
SHA256 mismatch for .agents/skills/my-skill/SKILL.md
```
**Cause:** Line ending differences (CRLF vs LF) between source and destination.
**Resolution:** Ensure consistent LF line endings in source skills. Use `git config core.autocrlf input`.

### install.sh: "Permission denied"
**Error:**
```
./install.sh: Permission denied
```
**Cause:** Script not executable.
**Resolution:** `chmod +x install.sh`

---

## Python Scripts

### ModuleNotFoundError: No module named 'xxx'
**Error:**
```
ModuleNotFoundError: No module named 'yaml'
```
**Cause:** Using non-stdlib imports in scripts/ (violates stdlib-only rule).
**Resolution:** Use only Python standard library. For YAML, use `json` or implement minimal parser.

### subprocess.CalledProcessError: Command 'git' failed
**Error:**
```
subprocess.CalledProcessError: Command '['git', 'rev-parse', '--show-toplevel']' returned non-zero exit status 128
```
**Cause:** Running outside a git repository.
**Resolution:** Ensure script runs from within git repo root, or handle gracefully.

---

## Cross-Platform Path Issues

### Windows: Backslash paths in npm scripts
**Error:**
```
npm ERR! path C:\Users\...\scripts\validate.py
```
**Cause:** Hardcoded backslashes in package.json scripts.
**Resolution:** Use forward slashes or `path` module in Python scripts.

### PowerShell: Variable expansion in npm config
**Error:**
```
npm config set //npm.pkg.github.com/:_authToken $token
```
**Cause:** PowerShell doesn't expand `$token` in cmd.exe context.
**Resolution:** Use `cmd /c` with `for /f` loop or set via environment variable.

---

## Skill Development

### "No runnable code fence found in skill body"
**Error:**
```
WARNING: .agents/skills/my-skill/SKILL.md: no runnable code fence found
```
**Cause:** Skill body missing ```python, ```bash, ```powershell, etc. fence.
**Resolution:** Add at least one runnable code example in skill body.

### "Keywords section missing"
**Error:**
```
WARNING: .agents/skills/my-skill/SKILL.md: Keywords: section required
```
**Cause:** Skill body missing `Keywords:` line.
**Resolution:** Add `Keywords: skill, agent, trigger` at end of skill body.

---

## Cross-Platform Shell & Environment

### PowerShell UTF-8 BOM in JSON Files
**Error:**
```
json.decoder.JSONDecodeError: Unexpected UTF-8 BOM (decode using utf-8-sig): line 1 column 1 (char 0)
```
**Cause:** PowerShell 5.1 `Set-Content -Encoding UTF8` automatically writes a UTF-8 byte-order mark (BOM) (`0xEF, 0xBB, 0xBF`), which breaks standard Python `json.load()` and POSIX tools expecting UTF-8.
**Resolution:** Write BOM-free UTF-8 explicitly using .NET:
```powershell
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($filePath, $content, $utf8NoBom)
```

### Windows App Execution Alias breaking Git Bash Python
**Error:**
```
Python was not found; run without arguments to install from the Microsoft Store, or disable this shortcut from Settings > Apps > Advanced app settings > App execution aliases.
```
**Cause:** In Git Bash on Windows, `python3` resolves to Windows Store placeholder shim `/c/Users/<user>/AppData/Local/Microsoft/WindowsApps/python3`.
**Resolution:** Never rely on ambient `python3` in POSIX shell scripts on Windows. Write JSON and parse receipts in pure POSIX shell (`cat`, `sed`, `awk`, `grep`).

### Windows cp1256 / Console Unicode Crashes
**Error:**
```
UnicodeEncodeError: 'charmap' codec can't encode characters in position ...: character maps to <undefined>
```
**Cause:** Default Windows console code pages (such as cp1256 or cp1252) cannot encode Unicode box-drawing or special characters without explicit stream reconfiguring.
**Resolution:**
Reconfigure console streams on entry in CLI scripts:
```python
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
```
Always specify `encoding="utf-8", errors="replace"` when capturing subprocess output.

### Anti-Premature Completion Loophole (Zero Assertions)
**Error:** Verification command exits with code 0 ("PASS") even when no verification contract was defined or assertions list was empty (`assertions: []`).
**Cause:** Defaulting to pass on empty assertions allows incomplete implementations to falsely pass CI/agent gates.
**Resolution:** In `verify_spec.py`, enforce that total assertions evaluated (`files_checked + commands_run`) must be strictly greater than 0, unless `--allow-empty` is explicitly passed.

### Git Worktree Hook Installation (EXDEV & Missing Hooks Dir)
**Error:**
```
OSError: [Errno 18] Invalid cross-device link
```
**Cause:** Git worktrees store a pointer file at `.git` rather than a directory, and moving temp files across volumes or non-existent directories causes `EXDEV` or `FileNotFoundError`.
**Resolution:** Resolve hook directory dynamically via `git rev-parse --git-dir` + `/hooks`, and write temporary atomic files directly in `target.parent`.

---

## Maintenance Notes

| Error Pattern | Frequency | Last Seen | Status |
|---------------|-----------|-----------|--------|
| Anti-Premature Completion (Zero Assertions) | High | 2026-09-23 | Resolved |
| Windows cp1256 / Console Unicode Crash | High | 2026-09-23 | Resolved |
| Git Worktree EXDEV on Hook Install | Medium | 2026-09-23 | Resolved |
| npm ENEEDAUTH | High | 2026-09-14 | Documented |
| Tag force-push | Medium | 2026-09-14 | Documented |
| OIDC id-token | Medium | 2026-09-14 | Documented |
| GitHub Packages Actions access | Low | 2026-09-14 | Documented |
| validate.py frontmatter | High | Ongoing | Enforced by CI |
| release_sync drift | Medium | Ongoing | Enforced by CI |

---

*Update this file when new error patterns are discovered. Each entry should include: Error output, Root cause, Resolution steps, Prevention.*