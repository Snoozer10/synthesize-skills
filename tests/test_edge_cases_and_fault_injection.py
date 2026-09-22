"""Test edge cases, failure modes, and fault injection for the standards engine. Stdlib only.

Run: python tests/test_edge_cases_and_fault_injection.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from discover_standards import discover_standards
from inject_standards import format_standards_markdown, estimate_tokens
from verify_spec import verify_spec


def test_empty_dir_discovery():
    """Discovering in an empty directory should return default envelope and not crash."""
    with tempfile.TemporaryDirectory() as td:
        empty = Path(td)
        st = discover_standards(empty, force=True)
        assert st["files_scanned"] == 0
        assert "response_envelope" in st
        assert len(st["error_codes"]) == 0


def test_token_trimming_edge_case():
    """Massive standards data must be trimmed deterministically to stay <= 600 tokens."""
    huge_standards = {
        "response_envelope": {"status": "str", "data": "any", "error": "any", "meta": "dict"},
        "error_codes": [f"ERR_CODE_{i}_{'x'*30}" for i in range(100)],
        "database_patterns": [f"query_method_{i}_{'y'*30}" for i in range(50)],
        "naming_conventions": {f"key_{i}": f"val_{i}_{'z'*20}" for i in range(20)}
    }
    output = format_standards_markdown(huge_standards, max_tokens=600)
    toks = estimate_tokens(output)
    assert toks <= 600, f"Token ceiling breached: {toks} > 600"
    assert "API Response Envelope:" in output


def test_missing_spec_verification():
    """verify_spec on nonexistent directory should report error and fail gracefully."""
    with tempfile.TemporaryDirectory() as td:
        missing = Path(td) / "specs" / "does-not-exist"
        passed, report = verify_spec(missing)
        assert passed is False
        assert "error" in report


def test_failing_assertion_verification():
    """verify_spec with a failing command should capture stdout, stderr, and exit 1."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        spec_dir = tmp / "specs" / "broken"
        spec_dir.mkdir(parents=True, exist_ok=True)
        
        v_data = {
            "slug": "broken",
            "title": "Broken Spec",
            "assertions": {
                "files_exist": ["nonexistent_file_xyz.txt"],
                "commands": ["exit 42"]
            }
        }
        (spec_dir / "VERIFICATION.json").write_text(json.dumps(v_data), encoding="utf-8")
        
        passed, report = verify_spec(spec_dir)
        assert passed is False
        assert "nonexistent_file_xyz.txt" in report["files_missing"]
        assert len(report["command_failures"]) > 0
        assert report["command_failures"][0]["exit_code"] != 0


if __name__ == "__main__":
    tests = [
        ("test_empty_dir_discovery", test_empty_dir_discovery),
        ("test_token_trimming_edge_case", test_token_trimming_edge_case),
        ("test_missing_spec_verification", test_missing_spec_verification),
        ("test_failing_assertion_verification", test_failing_assertion_verification),
    ]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS: {name}")
        except Exception as e:
            print(f"FAIL: {name}: {e}")
            failed += 1
    sys.exit(1 if failed else 0)
