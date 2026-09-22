"""Pressure tests for repo-standards-engineer engine — stdlib only.

Run: python tests/test_standards_engine.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / ".agents" / "skills" / "repo-standards-engineer"
DISCOVER_PY = REPO_ROOT / "scripts" / "discover_standards.py"
INJECT_PY = REPO_ROOT / "scripts" / "inject_standards.py"
SHAPE_SPEC_PY = REPO_ROOT / "scripts" / "shape_spec.py"
VERIFY_SPEC_PY = REPO_ROOT / "scripts" / "verify_spec.py"


def _run(cwd: Path, script: Path, args=None):
    cmd = [sys.executable, str(script)] + list(args or [])
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, shell=False)


def _setup_sample_project(tmp: Path):
    """Creates a sample python + js codebase to verify standards discovery."""
    src = tmp / "src"
    src.mkdir(parents=True, exist_ok=True)
    
    # Python API endpoint with envelope pattern and error enum
    (src / "api.py").write_text("""\
from enum import Enum

class ErrorCode(str, Enum):
    INVALID_PAYLOAD = "ERR_INVALID_PAYLOAD"
    NOT_FOUND = "ERR_NOT_FOUND"

def make_response(data=None, error=None):
    return {
        "status": "error" if error else "success",
        "data": data,
        "error": error,
        "meta": {"version": "v1"}
    }
""", encoding="utf-8")

    # JS/TS file with response pattern
    (src / "client.js").write_text("""\
export async function fetchData(id) {
    const res = await fetch(`/api/items/${id}`);
    const json = await res.json();
    if (json.status !== "success") {
        throw new Error(json.error || "UNKNOWN_ERROR");
    }
    return json.data;
}
""", encoding="utf-8")


def test_standards_discovery_ast():
    """discover_standards.py must extract response envelope and error patterns with SHA-256 caching."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _setup_sample_project(tmp)
        
        res = _run(tmp, DISCOVER_PY, ["--json"])
        assert res.returncode == 0, f"Expected exit 0, got {res.returncode}: {res.stderr}"
        data = json.loads(res.stdout)
        
        assert "response_envelope" in data, "Must detect response_envelope"
        assert "error_codes" in data, "Must detect error_codes"
        assert "ERR_INVALID_PAYLOAD" in data["error_codes"], "Must detect ERR_INVALID_PAYLOAD"
        assert "cache_sha256" in data, "Must include content-addressed cache_sha256"
        
        # Verify cached execution is fast and matches
        res2 = _run(tmp, DISCOVER_PY, ["--json"])
        assert res2.returncode == 0
        data2 = json.loads(res2.stdout)
        assert data2["cache_sha256"] == data["cache_sha256"], "Cache hash must match"


def test_token_bounded_injection():
    """inject_standards.py must generate markdown standard injection <= 600 tokens."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _setup_sample_project(tmp)
        
        # First discover
        _run(tmp, DISCOVER_PY)
        
        # Inject
        res = _run(tmp, INJECT_PY, ["--max-tokens", "600"])
        assert res.returncode == 0, f"Expected exit 0, got {res.returncode}: {res.stderr}"
        output = res.stdout
        
        assert "Response Envelope:" in output or "status" in output, "Must contain envelope summary"
        assert "Error Codes:" in output or "ERR_" in output, "Must contain error codes"
        
        # Approx token calculation (1 token ~= 4 chars or 0.75 words)
        words = len(output.split())
        est_tokens = max(words * 1.3, len(output) / 3.8)
        assert est_tokens <= 600, f"Token ceiling violated: estimated {est_tokens} tokens (max 600)"


def test_spec_shaper_and_verification():
    """shape_spec.py generates spec and verify_spec.py verifies deterministic contract."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _setup_sample_project(tmp)
        
        # Shape a spec
        res = _run(tmp, SHAPE_SPEC_PY, [
            "--slug", "user-auth",
            "--title", "User Authentication",
            "--criterion", "File src/api.py exists",
            "--assert-file", "src/api.py"
        ])
        assert res.returncode == 0, f"Shape spec failed: {res.stderr}"
        
        spec_file = tmp / "specs" / "user-auth" / "SPEC.md"
        assert spec_file.is_file(), "SPEC.md must be created"
        
        # Verify spec contract passes
        v_res = _run(tmp, VERIFY_SPEC_PY, ["--spec", str(spec_file.parent)])
        assert v_res.returncode == 0, f"Verification failed: {v_res.stdout} {v_res.stderr}"
        assert "CONTRACT PASSED" in v_res.stdout, "Must confirm contract passed"
        
        # Negative test: assert non-existent file causes contract failure
        neg_res = _run(tmp, SHAPE_SPEC_PY, [
            "--slug", "failing-feature",
            "--title", "Failing Feature",
            "--assert-file", "src/nonexistent.py"
        ])
        assert neg_res.returncode == 0
        
        neg_spec = tmp / "specs" / "failing-feature"
        v_neg = _run(tmp, VERIFY_SPEC_PY, ["--spec", str(neg_spec)])
        assert v_neg.returncode == 1, "Must exit 1 on contract failure"
        assert "CONTRACT FAILED" in v_neg.stdout or "CONTRACT FAILED" in v_neg.stderr


if __name__ == "__main__":
    failed = 0
    for name, fn in [
        ("test_standards_discovery_ast", test_standards_discovery_ast),
        ("test_token_bounded_injection", test_token_bounded_injection),
        ("test_spec_shaper_and_verification", test_spec_shaper_and_verification),
    ]:
        try:
            fn()
            print(f"PASS: {name}")
        except AssertionError as e:
            print(f"FAIL: {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"FAIL: {name}: {e}")
            failed += 1
    sys.exit(1 if failed else 0)
