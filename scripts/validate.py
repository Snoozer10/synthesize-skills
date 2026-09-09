"""Validate skill dirs. Stdlib only. Prints PASS/FAIL per skill. Exit 1 on any ERROR."""
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RUNNABLE_RE = re.compile(r"```(python|py|bash|sh|powershell|ps1|js|ts)\b", re.IGNORECASE)
SKIP_DIRS = {"references", "scripts", "__pycache__", ".git", "node_modules"}

ERROR = "ERROR"
WARN = "WARN"


def parse_frontmatter(text):
    if not text.startswith("---"):
        return None, None, "missing frontmatter fences"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, None, "unclosed frontmatter fence"
    raw = parts[1]
    body = parts[2]
    fm = {}
    for lineno, line in enumerate(raw.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if ":" not in s:
            return None, raw, "YAML parse fail line %d: %r" % (lineno, line)
        k, v = s.split(":", 1)
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, raw, None


def find_skills(root):
    root = Path(root)
    out = []
    for p in root.rglob("SKILL.md"):
        if any(d in SKIP_DIRS for d in p.parts):
            continue
        out.append(p.parent)
    return sorted(out)


def validate_skill(sdir):
    errors = []
    warns = []
    sdir = Path(sdir)
    f = sdir / "SKILL.md"
    if not f.is_file():
        return ["missing SKILL.md"], []
    text = f.read_text(encoding="utf-8")
    fm, raw, perr = parse_frontmatter(text)
    if perr:
        return ["YAML parse fail: " + perr], []
    name = fm.get("name", "")
    desc = fm.get("description", "")
    if not NAME_RE.match(name):
        errors.append("name regex fail: %r" % name)
    if sdir.name != name:
        # template dir uses placeholder dir name; allow skill-template dir
        if not (sdir.name == "skill-template" and name == "skill-name"):
            errors.append("dir mismatch: dir %r != name %r" % (sdir.name, name))
    if not (1 <= len(desc) <= 500):
        errors.append("description 1-500 chars fail: got %d" % len(desc))
    if len(raw) > 1024:
        errors.append("frontmatter <=1024 chars fail: got %d" % len(raw))
    body = text.split("---", 2)[2] if text.startswith("---") else text
    if len(body.splitlines()) >= 500:
        errors.append("body <500 lines fail")
    if not RUNNABLE_RE.search(body):
        errors.append("runnable code fence missing (need python|bash|sh|ps1|js|ts)")
    # WARNINGS only
    if not desc.startswith("Use when"):
        warns.append("description should start with 'Use when'")
    if re.search(r"(^|\s)I (can|will|help|am)\b", desc):
        warns.append("third-person: avoid first-person in description")
    if re.search(r"workflow|step.by.step|first.*then.*finally", body, re.IGNORECASE):
        warns.append("workflow-summary: description/body may summarize process")
    if "Keywords" not in body and "keywords" not in body:
        warns.append("keywords: add searchable error/symptom/tool terms")
    if "@skills" in body or re.search(r"@[\w-]+/", body):
        warns.append("@skill-slug links: prefer skill name reference over @ links")
    return errors, warns


def main(argv):
    root = Path(argv[1]) if len(argv) > 1 else Path(".")
    skills = find_skills(root)
    if not skills:
        print("FAIL: no skills found under '%s'" % root)
        return 1
    failed = 0
    for s in skills:
        errs, warns = validate_skill(s)
        for w in warns:
            print("%s: %s: %s %s" % (WARN, s, "warning", w))
        if errs:
            failed += 1
            for e in errs:
                print("%s: %s: %s" % (ERROR, s, e))
            print("FAIL: %s" % s)
        else:
            print("PASS: %s" % s)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
