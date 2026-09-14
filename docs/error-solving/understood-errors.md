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

### npm publish: "You must verify your email"
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

## Maintenance Notes

| Error Pattern | Frequency | Last Seen | Status |
|---------------|-----------|-----------|--------|
| npm ENEEDAUTH | High | 2026-09-14 | Documented |
| Tag force-push | Medium | 2026-09-14 | Documented |
| OIDC id-token | Medium | 2026-09-14 | Documented |
| GitHub Packages Actions access | Low | 2026-09-14 | Documented |
| validate.py frontmatter | High | Ongoing | Enforced by CI |
| release_sync drift | Medium | Ongoing | Enforced by CI |

---

*Update this file when new error patterns are discovered. Each entry should include: Error output, Root cause, Resolution steps, Prevention.*