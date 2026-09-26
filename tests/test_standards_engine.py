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
CHECK_COMPLIANCE_PY = REPO_ROOT / "scripts" / "check_compliance.py"


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


def test_standards_compliance_checker():
    """check_compliance.py must verify error codes, response envelopes, and DB patterns."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        src = tmp / "src"
        src.mkdir(parents=True, exist_ok=True)

        # 1. Establish standards in baseline file
        (src / "base.py").write_text("""\
from enum import Enum

class ErrorCode(str, Enum):
    VALID_A = "ERR_VALID_A"
    VALID_B = "ERR_VALID_B"

def respond(data=None, error=None):
    return {
        "status": "error" if error else "success",
        "data": data,
        "error": error
    }

class Repo:
    def execute(self, query):
        pass

def run_query(repo):
    return repo.execute("SELECT 1")
""", encoding="utf-8")

        # Discover standards to create standards_cache.json
        res_disc = _run(tmp, DISCOVER_PY, ["--json"])
        assert res_disc.returncode == 0, f"Discovery failed: {res_disc.stderr}"
        standards = json.loads(res_disc.stdout)
        assert "ERR_VALID_A" in standards["error_codes"]
        assert "status" in standards["response_envelope"]
        assert "execute" in standards["database_patterns"]

        # 2. Compliant file passes
        (src / "compliant.py").write_text("""\
def get_user():
    return {
        "status": "success",
        "data": {"id": 1, "name": "Alice"}
    }

def fail_user():
    return {
        "status": "error",
        "error": "ERR_VALID_A"
    }
""", encoding="utf-8")

        res_comp = _run(tmp, CHECK_COMPLIANCE_PY, ["--files", "src/compliant.py", "--json"])
        assert res_comp.returncode == 0, f"Compliant file failed with exit {res_comp.returncode}: {res_comp.stdout} {res_comp.stderr}"
        data_comp = json.loads(res_comp.stdout)
        assert data_comp["compliant"] is True
        assert data_comp["violations_count"] == 0
        assert len(data_comp["violations"]) == 0

        # Also verify programmatic check_compliance invocation
        if str(REPO_ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from check_compliance import check_compliance
        is_ok, report = check_compliance(tmp, target_files=[src / "compliant.py"])
        assert is_ok is True
        assert report["compliant"] is True
        assert report["violations_count"] == 0

        # 3. Undeclared error code violation
        (src / "alien_error.py").write_text("""\
def raise_alien():
    return {
        "status": "error",
        "error": "ERR_ALIEN_CODE"
    }
""", encoding="utf-8")

        res_alien = _run(tmp, CHECK_COMPLIANCE_PY, ["--files", "src/alien_error.py", "--json"])
        assert res_alien.returncode == 1, f"Expected exit 1 for undeclared error code, got {res_alien.returncode}"
        data_alien = json.loads(res_alien.stdout)
        assert data_alien["compliant"] is False
        assert data_alien["violations_count"] >= 1
        rules = [v["rule"] for v in data_alien["violations"]]
        assert "UNDECLARED_ERROR_CODE" in rules
        violation = next(v for v in data_alien["violations"] if v["rule"] == "UNDECLARED_ERROR_CODE")
        assert "ERR_ALIEN_CODE" in violation["message"]

        # 4. Malformed response envelope violation (conflicting key: result)
        (src / "malformed_envelope.py").write_text("""\
def bad_envelope():
    return {
        "result": "ok"
    }
""", encoding="utf-8")

        res_env = _run(tmp, CHECK_COMPLIANCE_PY, ["--files", "src/malformed_envelope.py", "--json"])
        assert res_env.returncode == 1, f"Expected exit 1 for malformed envelope, got {res_env.returncode}"
        data_env = json.loads(res_env.stdout)
        assert data_env["compliant"] is False
        assert any(v["rule"] == "MALFORMED_RESPONSE_ENVELOPE" for v in data_env["violations"])

        # 5. Malformed response envelope violation (invalid status value)
        (src / "bad_status.py").write_text("""\
def bad_status():
    return {
        "status": "pending",
        "data": None
    }
""", encoding="utf-8")

        res_status = _run(tmp, CHECK_COMPLIANCE_PY, ["--files", "src/bad_status.py", "--json"])
        assert res_status.returncode == 1, f"Expected exit 1 for invalid status value, got {res_status.returncode}"
        data_status = json.loads(res_status.stdout)
        assert data_status["compliant"] is False
        assert any(v["rule"] == "MALFORMED_RESPONSE_ENVELOPE" for v in data_status["violations"])

        # 6. Prohibited DB method violation
        (src / "bad_db.py").write_text("""\
def direct_query(cursor):
    return cursor.execute_sql("SELECT 1")
""", encoding="utf-8")

        res_db = _run(tmp, CHECK_COMPLIANCE_PY, ["--files", "src/bad_db.py", "--json"])
        assert res_db.returncode == 1, f"Expected exit 1 for prohibited DB method, got {res_db.returncode}"
        data_db = json.loads(res_db.stdout)
        assert data_db["compliant"] is False
        assert any(v["rule"] == "PROHIBITED_DB_METHOD" for v in data_db["violations"])


def test_shape_spec_from_standards():
    """shape_spec.py must auto-wire standards (--from-standards) and support rich semantic assertion flags."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        src = tmp / "src"
        src.mkdir(parents=True, exist_ok=True)

        # 1. Establish mock repository with standards (response envelope, error codes, DB patterns)
        (src / "app.py").write_text("""\
from enum import Enum

class AppError(str, Enum):
    INVALID_INPUT = "ERR_INVALID_INPUT"
    UNAUTHORIZED = "ERR_UNAUTHORIZED"

def make_response(data=None, error=None):
    return {
        "status": "error" if error else "success",
        "data": data,
        "error": error
    }

class UserRepository:
    def execute(self, query):
        pass
    def query(self, sql):
        pass

def run_query(repo):
    return repo.execute("SELECT 1")
""", encoding="utf-8")

        # 2. Test programmatic API with from_standards=True and assert_files
        if str(REPO_ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from shape_spec import shape_spec

        spec_dir = shape_spec(
            root=tmp,
            slug="user-feature",
            title="User Feature Implementation",
            assert_files=["src/app.py"],
            from_standards=True
        )

        spec_md = (spec_dir / "SPEC.md").read_text(encoding="utf-8")
        assert "Code adheres to discovered response envelope" in spec_md, "SPEC.md must contain response envelope criterion"
        assert "Error handling adheres to declared error code standards" in spec_md, "SPEC.md must contain error code criterion"
        assert "Database interactions follow approved query methods" in spec_md, "SPEC.md must contain database patterns criterion"
        assert "Passes repository standards compliance check without drift." in spec_md, "SPEC.md must contain general compliance criterion"

        v_data = json.loads((spec_dir / "VERIFICATION.json").read_text(encoding="utf-8"))
        assertions = v_data["assertions"]
        assert "python scripts/check_compliance.py --files src/app.py" in assertions["commands"], "VERIFICATION.json commands must contain compliance check"
        assert "files_exist" in assertions
        assert "file_contains" in assertions
        assert "regex_matches" in assertions
        assert "json_matches" in assertions
        assert "ast_symbol_present" in assertions

        # 3. Test CLI execution with --from-standards, --assert-contains, --assert-symbol, --assert-regex
        (tmp / "config.json").write_text(json.dumps({"version": 1, "enabled": True}), encoding="utf-8")

        res = _run(tmp, SHAPE_SPEC_PY, [
            "--slug", "cli-scaffolded",
            "--title", "CLI Scaffolded Feature",
            "--from-standards",
            "--assert-file", "src/app.py",
            "--assert-contains", "src/app.py:class UserRepository",
            "--assert-symbol", "src/app.py:UserRepository:ClassDef",
            "--assert-regex", r"src/app.py:class\s+UserRepository",
            "--assert-json", 'config.json:{"enabled": true}'
        ])
        assert res.returncode == 0, f"CLI shape_spec failed: {res.stderr}\n{res.stdout}"

        cli_spec_dir = tmp / "specs" / "cli-scaffolded"
        assert (cli_spec_dir / "SPEC.md").is_file()
        cli_v_data = json.loads((cli_spec_dir / "VERIFICATION.json").read_text(encoding="utf-8"))
        cli_assertions = cli_v_data["assertions"]

        assert any(any("UserRepository" in text for text in item.get("contains", [])) for item in cli_assertions["file_contains"]), "Must populate file_contains"
        assert any(item["name"] == "UserRepository" for item in cli_assertions["ast_symbol_present"]), "Must populate ast_symbol_present"
        assert any("UserRepository" in item["pattern"] for item in cli_assertions["regex_matches"]), "Must populate regex_matches"
        assert any(item["subset"] == {"enabled": True} for item in cli_assertions["json_matches"]), "Must populate json_matches"
        assert "python scripts/check_compliance.py --files src/app.py" in cli_assertions["commands"], "Must include compliance command in CLI spec"


if __name__ == "__main__":
    failed = 0
    for name, fn in [
        ("test_standards_discovery_ast", test_standards_discovery_ast),
        ("test_pydantic_and_typed_ast_discovery", test_pydantic_and_typed_ast_discovery),
        ("test_token_bounded_injection", test_token_bounded_injection),
        ("test_spec_shaper_and_verification", test_spec_shaper_and_verification),
        ("test_rich_semantic_contract_assertions", test_rich_semantic_contract_assertions),
        ("test_standards_compliance_checker", test_standards_compliance_checker),
        ("test_shape_spec_from_standards", test_shape_spec_from_standards),
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


