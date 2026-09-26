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


def test_pydantic_and_typed_ast_discovery():
    """discover_standards.py must extract Pydantic/TypedDict envelopes, custom exceptions, TS enums/interfaces, and DB patterns."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        src = tmp / "src"
        src.mkdir(parents=True, exist_ok=True)
        
        # Python file with Pydantic BaseModel, Dataclass, TypedDict, and Custom Exception
        (src / "models.py").write_text("""\
from dataclasses import dataclass
from typing import TypedDict, Optional
from pydantic import BaseModel

class CustomAppError(Exception):
    code = "ERR_CUSTOM_EXCEPTION"
    default_code = "ERR_DEFAULT_EXCEPTION"

@dataclass
class ItemDto:
    id: str
    name: str

class MetaInfo(TypedDict):
    version: str
    timestamp: int

class ApiResponseModel(BaseModel):
    status: str
    data: Optional[dict] = None
    error: Optional[str] = None
    meta: Optional[MetaInfo] = None
""", encoding="utf-8")

        # TypeScript file with enum, interface response envelope, and DB query pattern
        (src / "service.ts").write_text("""\
export enum ErrorCode {
    TS_UNAUTHORIZED = "ERR_TS_UNAUTHORIZED",
    TS_NOT_FOUND = "ERR_TS_NOT_FOUND",
}

export interface ApiResponse<T> {
    status: "success" | "error";
    data: T;
    error?: string;
    meta?: Record<string, any>;
}

export class UserService {
    async getUsers(db: any) {
        return await db.findMany();
    }
}
""", encoding="utf-8")

        res = _run(tmp, DISCOVER_PY, ["--json"])
        assert res.returncode == 0, f"Expected exit 0, got {res.returncode}: {res.stderr}"
        data = json.loads(res.stdout)
        
        # Verify error codes
        assert "ERR_CUSTOM_EXCEPTION" in data["error_codes"], f"Must detect ERR_CUSTOM_EXCEPTION in {data['error_codes']}"
        assert "ERR_DEFAULT_EXCEPTION" in data["error_codes"], f"Must detect ERR_DEFAULT_EXCEPTION in {data['error_codes']}"
        assert "ERR_TS_UNAUTHORIZED" in data["error_codes"], f"Must detect ERR_TS_UNAUTHORIZED in {data['error_codes']}"
        assert "ERR_TS_NOT_FOUND" in data["error_codes"], f"Must detect ERR_TS_NOT_FOUND in {data['error_codes']}"
        
        # Verify response envelope keys
        envelope_keys = set(data["response_envelope"].keys())
        for key in ("status", "data", "error", "meta"):
            assert key in envelope_keys, f"Response envelope missing '{key}': {envelope_keys}"
            
        # Verify DB query pattern
        assert "findMany" in data["database_patterns"], f"Must detect findMany in {data['database_patterns']}"
        
        # Verify caching
        assert "cache_sha256" in data, "Must include cache_sha256"
        res2 = _run(tmp, DISCOVER_PY, ["--json"])
        assert res2.returncode == 0
        data2 = json.loads(res2.stdout)
        assert data2["cache_sha256"] == data["cache_sha256"], "Cache hash must match"


def test_rich_semantic_contract_assertions():
    """verify_spec.py must execute rich semantic assertions (file_contains, regex_matches, json_matches, ast_symbol_present)."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        
        # 1. Setup sample files
        (tmp / "sample.txt").write_text("Hello World! This is a test file for rich semantic assertions.", encoding="utf-8")
        (tmp / "sample.json").write_text(json.dumps({
            "status": "success",
            "data": {
                "count": 10,
                "items": ["a"]
            }
        }), encoding="utf-8")
        (tmp / "sample.py").write_text("""\
class UserDto:
    pass

async def fetch_user(user_id: str):
    return {"id": user_id}

MAX_RETRIES = 3
""", encoding="utf-8")

        spec_dir = tmp / "specs" / "rich-contract"
        spec_dir.mkdir(parents=True, exist_ok=True)

        # 2. Positive case: all assertions match
        positive_contract = {
            "slug": "rich-contract",
            "title": "Rich Semantic Verification Contract",
            "created_at": "2026-09-24",
            "assertions": {
                "files_exist": ["sample.txt", "sample.json", "sample.py"],
                "file_contains": [
                    {"file": "sample.txt", "contains": ["Hello World", "rich semantic assertions"]}
                ],
                "regex_matches": [
                    {"file": "sample.txt", "pattern": r"Hello\s+World.*test\s+file"}
                ],
                "json_matches": [
                    {"file": "sample.json", "subset": {"status": "success", "data": {"count": 10}}}
                ],
                "ast_symbol_present": [
                    {"file": "sample.py", "name": "UserDto", "type": "class"},
                    {"file": "sample.py", "name": "fetch_user", "type": "function"},
                    {"file": "sample.py", "name": "MAX_RETRIES", "type": "variable"}
                ]
            }
        }
        (spec_dir / "VERIFICATION.json").write_text(json.dumps(positive_contract, indent=2), encoding="utf-8")

        res = _run(tmp, VERIFY_SPEC_PY, ["--spec", str(spec_dir), "--json"])
        assert res.returncode == 0, f"Expected positive contract to pass (exit 0), got {res.returncode}: {res.stderr}\n{res.stdout}"
        data = json.loads(res.stdout)
        assert data["status"] == "PASSED", f"Expected PASSED, got {data['status']}"
        assert data["files_checked"] == 3
        assert data["assertions_checked"] == 6
        assert len(data["assertion_failures"]) == 0

        # Also verify non-json stdout formatting
        res_text = _run(tmp, VERIFY_SPEC_PY, ["--spec", str(spec_dir)])
        assert res_text.returncode == 0
        assert "CONTRACT PASSED: rich-contract" in res_text.stdout
        assert "Verified 3 files present." in res_text.stdout

        # 3. Negative cases for each assertion type
        
        # 3a. file_contains failure
        neg_contains = dict(positive_contract)
        neg_contains["assertions"] = {
            "file_contains": [{"file": "sample.txt", "contains": ["NONEXISTENT_PHRASE"]}]
        }
        (spec_dir / "VERIFICATION.json").write_text(json.dumps(neg_contains), encoding="utf-8")
        res = _run(tmp, VERIFY_SPEC_PY, ["--spec", str(spec_dir), "--json"])
        assert res.returncode == 1, "Expected exit 1 on file_contains failure"
        data = json.loads(res.stdout)
        assert data["status"] == "FAILED"
        assert len(data["assertion_failures"]) == 1
        assert data["assertion_failures"][0]["type"] == "file_contains"

        # 3b. regex_matches failure
        neg_regex = dict(positive_contract)
        neg_regex["assertions"] = {
            "regex_matches": [{"file": "sample.txt", "pattern": r"^Goodbye\s+World"}]
        }
        (spec_dir / "VERIFICATION.json").write_text(json.dumps(neg_regex), encoding="utf-8")
        res = _run(tmp, VERIFY_SPEC_PY, ["--spec", str(spec_dir), "--json"])
        assert res.returncode == 1, "Expected exit 1 on regex_matches failure"
        data = json.loads(res.stdout)
        assert data["status"] == "FAILED"
        assert len(data["assertion_failures"]) == 1
        assert data["assertion_failures"][0]["type"] == "regex_matches"

        # 3c. json_matches failure (subset mismatch)
        neg_json = dict(positive_contract)
        neg_json["assertions"] = {
            "json_matches": [{"file": "sample.json", "subset": {"data": {"count": 999}}}]
        }
        (spec_dir / "VERIFICATION.json").write_text(json.dumps(neg_json), encoding="utf-8")
        res = _run(tmp, VERIFY_SPEC_PY, ["--spec", str(spec_dir), "--json"])
        assert res.returncode == 1, "Expected exit 1 on json_matches failure"
        data = json.loads(res.stdout)
        assert data["status"] == "FAILED"
        assert len(data["assertion_failures"]) == 1
        assert data["assertion_failures"][0]["type"] == "json_matches"

        # 3d. ast_symbol_present failure (missing symbol)
        neg_ast = dict(positive_contract)
        neg_ast["assertions"] = {
            "ast_symbol_present": [{"file": "sample.py", "name": "MissingClass", "type": "class"}]
        }
        (spec_dir / "VERIFICATION.json").write_text(json.dumps(neg_ast), encoding="utf-8")
        res = _run(tmp, VERIFY_SPEC_PY, ["--spec", str(spec_dir), "--json"])
        assert res.returncode == 1, "Expected exit 1 on ast_symbol_present failure"
        data = json.loads(res.stdout)
        assert data["status"] == "FAILED"
        assert len(data["assertion_failures"]) == 1
        assert data["assertion_failures"][0]["type"] == "ast_symbol_present"

        # 3e. ast_symbol_present failure (wrong type)
        neg_ast_type = dict(positive_contract)
        neg_ast_type["assertions"] = {
            "ast_symbol_present": [{"file": "sample.py", "name": "UserDto", "type": "function"}]
        }
        (spec_dir / "VERIFICATION.json").write_text(json.dumps(neg_ast_type), encoding="utf-8")
        res = _run(tmp, VERIFY_SPEC_PY, ["--spec", str(spec_dir), "--json"])
        assert res.returncode == 1, "Expected exit 1 on ast_symbol_present wrong type"
        data = json.loads(res.stdout)
        assert data["status"] == "FAILED"
        assert len(data["assertion_failures"]) == 1
        assert data["assertion_failures"][0]["type"] == "ast_symbol_present"


if __name__ == "__main__":
    failed = 0
    for name, fn in [
        ("test_standards_discovery_ast", test_standards_discovery_ast),
        ("test_pydantic_and_typed_ast_discovery", test_pydantic_and_typed_ast_discovery),
        ("test_token_bounded_injection", test_token_bounded_injection),
        ("test_spec_shaper_and_verification", test_spec_shaper_and_verification),
        ("test_rich_semantic_contract_assertions", test_rich_semantic_contract_assertions),
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

