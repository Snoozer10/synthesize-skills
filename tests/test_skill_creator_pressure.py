"""Pressure tests for skill-creator and init_skill.py scaffolding utility."""

import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_invalid_skill_name_rejected():
    init_script = ROOT / "scripts" / "init_skill.py"
    if not init_script.exists():
        init_script = ROOT / ".agents" / "skills" / "skill-creator" / "scripts" / "init_skill.py"

    invalid_names = ["InvalidName", "foo_bar", "foo--bar", "-start-hyphen", "end-hyphen-", "123_456"]
    with tempfile.TemporaryDirectory() as td:
        for name in invalid_names:
            cmd = [sys.executable, str(init_script), name, "--dest", td]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            if res.returncode == 0:
                print(f"FAIL: Expected failure for invalid name '{name}', but succeeded!")
                sys.exit(1)
    print("PASS: test_invalid_skill_name_rejected")


def test_skill_scaffolding_deterministic():
    init_script = ROOT / "scripts" / "init_skill.py"
    if not init_script.exists():
        init_script = ROOT / ".agents" / "skills" / "skill-creator" / "scripts" / "init_skill.py"

    with tempfile.TemporaryDirectory() as td:
        target_dir = pathlib.Path(td)
        cmd = [
            sys.executable,
            str(init_script),
            "sample-skill",
            "--dest",
            str(target_dir),
            "--desc",
            "Use when testing automated skill scaffolding and validation workflows.",
            "--keywords",
            "sample, scaffolding, testing",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if res.returncode != 0:
            print(f"FAIL: init_skill exited with {res.returncode}: {res.stderr}")
            sys.exit(1)

        skill_dir = target_dir / "sample-skill"
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            print(f"FAIL: SKILL.md not found at {skill_md}")
            sys.exit(1)

        content = skill_md.read_text(encoding="utf-8")
        if "name: sample-skill" not in content:
            print("FAIL: 'name: sample-skill' missing from frontmatter")
            sys.exit(1)
        if "Use when" not in content:
            print("FAIL: 'Use when' missing from frontmatter description")
            sys.exit(1)
        if "## Keywords" not in content:
            print("FAIL: '## Keywords' section missing from body")
            sys.exit(1)
    print("PASS: test_skill_scaffolding_deterministic")


def test_scaffolded_skill_passes_validator():
    init_script = ROOT / "scripts" / "init_skill.py"
    if not init_script.exists():
        init_script = ROOT / ".agents" / "skills" / "skill-creator" / "scripts" / "init_skill.py"
    val_script = ROOT / "scripts" / "validate.py"

    with tempfile.TemporaryDirectory() as td:
        target_dir = pathlib.Path(td)
        cmd_init = [
            sys.executable,
            str(init_script),
            "validated-skill",
            "--dest",
            str(target_dir),
            "--desc",
            "Use when executing automated validation pressure tests across scaffolded skills.",
            "--keywords",
            "validator, pressure, automated",
        ]
        res_init = subprocess.run(cmd_init, capture_output=True, text=True, encoding="utf-8")
        if res_init.returncode != 0:
            print(f"FAIL: init failed: {res_init.stderr}")
            sys.exit(1)

        skill_dir = target_dir / "validated-skill"
        cmd_val = [sys.executable, str(val_script), str(skill_dir)]
        res_val = subprocess.run(cmd_val, capture_output=True, text=True, encoding="utf-8")
        if res_val.returncode != 0 or "WARN:" in res_val.stdout or "WARN:" in res_val.stderr:
            print(f"FAIL: validate.py failed or emitted warnings on scaffolded skill:\n{res_val.stdout}\n{res_val.stderr}")
            sys.exit(1)
    print("PASS: test_scaffolded_skill_passes_validator")


if __name__ == "__main__":
    test_invalid_skill_name_rejected()
    test_skill_scaffolding_deterministic()
    test_scaffolded_skill_passes_validator()
    print("ALL PASS")
