"""Test Multi-Host Adapter Compiler. Stdlib only.

Run: python tests/test_compile_adapters.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILE_PY = REPO_ROOT / "scripts" / "compile_adapters.py"


def test_compile_adapters_cli_and_targets():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        
        # Setup dummy skill
        skill_dir = tmp / ".agents" / "skills" / "sample-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text("""---
name: sample-skill
description: "Use when performing sample operations"
---
# Sample
""", encoding="utf-8")

        out_dir = tmp / "build" / "adapters"
        
        # Test with --out-dir and --root flags
        cmd = [
            sys.executable, str(COMPILE_PY),
            "--root", str(tmp),
            "--out-dir", str(out_dir)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"Failed: {res.stderr}"
        
        # Check generated adapter files across hosts
        assert (out_dir / ".claude" / "commands" / "sample-skill.md").is_file(), "Claude command missing"
        assert (out_dir / ".cursor" / "rules" / "sample-skill.mdc").is_file(), "Cursor rule missing"
        assert (out_dir / ".gemini" / "rules" / "sample-skill.md").is_file(), "Gemini rule missing"
        assert (out_dir / ".opencode" / "commands" / "sample-skill.md").is_file(), "OpenCode command missing"
        assert (out_dir / ".codex" / "instructions" / "sample-skill.md").is_file(), "Codex instruction missing"
        assert (out_dir / ".windsurf" / "rules" / "sample-skill.md").is_file(), "Windsurf rule missing"


if __name__ == "__main__":
    try:
        test_compile_adapters_cli_and_targets()
        print("PASS: test_compile_adapters_cli_and_targets")
        sys.exit(0)
    except Exception as e:
        print(f"FAIL: {e}")
        sys.exit(1)
