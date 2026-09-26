"""Pressure and Resilience Test Suite for repo-standards-engineer Engine.
Stdlib only. Tests polyglot repository pipeline, malformed syntax resilience,
and Windows unicode / special character safety.

Run:
    python -m unittest tests/test_standards_engine_pressure.py -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
DISCOVER_PY = SCRIPTS_DIR / "discover_standards.py"
INJECT_PY = SCRIPTS_DIR / "inject_standards.py"
SHAPE_SPEC_PY = SCRIPTS_DIR / "shape_spec.py"
VERIFY_SPEC_PY = SCRIPTS_DIR / "verify_spec.py"
CHECK_COMPLIANCE_PY = SCRIPTS_DIR / "check_compliance.py"
INDEX_PY = SCRIPTS_DIR / "index_standards.py"


def _run(cwd: Path, script: Path, args=None, env=None):
    """Run Python script with utf-8 encoding and isolated environment."""
    cmd = [sys.executable, str(script)] + list(args or [])
    run_env = os.environ.copy()
    run_env["PYTHONIOENCODING"] = "utf-8"
    run_env["PYTHONLEGACYWINDOWSSTDIO"] = "0"
    if env:
        run_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )


def _copy_scripts_to(target_dir: Path):
    """Copies repo standards scripts into temp directory so commands resolve locally."""
    target_scripts = target_dir / "scripts"
    target_scripts.mkdir(parents=True, exist_ok=True)
    for sname in [
        "discover_standards.py",
        "inject_standards.py",
        "shape_spec.py",
        "verify_spec.py",
        "check_compliance.py",
        "index_standards.py",
    ]:
        src_file = SCRIPTS_DIR / sname
        if src_file.is_file():
            shutil.copy2(src_file, target_scripts / sname)


class TestStandardsEnginePressure(unittest.TestCase):

    def test_polyglot_repository_e2e(self):
        """End-to-end pipeline across a polyglot project (Python + TypeScript).

        Verifies:
        1. Multi-paradigm discovery (Pydantic, @dataclass, TypedDict, Exception hierarchy, TS enums/interfaces).
        2. Spec shaping with auto-wired standards (--from-standards).
        3. Compliance checking (clean pass on conforming code, violation receipt on non-conforming code).
        4. Spec contract verification (full pass).
        5. Reverse symbol & error code indexing lookups.
        """
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _copy_scripts_to(tmp)
            src = tmp / "src"
            src.mkdir(parents=True, exist_ok=True)

            # Python: Models & Typed Structures
            (src / "models.py").write_text(
                """\
from pydantic import BaseModel
from dataclasses import dataclass
from typing import TypedDict

class UserPayload(BaseModel):
    id: int
    username: str
    email: str

@dataclass
class ServerConfig:
    host: str
    port: int

class RequestOptions(TypedDict):
    timeout: int
    retries: int
""",
                encoding="utf-8",
            )

            # Python: Exceptions with Class Error Codes
            (src / "errors.py").write_text(
                """\
class ApplicationError(Exception):
    code = "ERR_BASE_APPLICATION"

class UnauthorizedError(ApplicationError):
    code = "ERR_UNAUTHORIZED"

class NotFoundError(ApplicationError):
    code = "ERR_NOT_FOUND"
""",
                encoding="utf-8",
            )

            # Python: Repository with Database Query Patterns
            (src / "repository.py").write_text(
                """\
class UserRepository:
    def query(self, sql: str):
        return []
    def fetch_all(self, query: str):
        return []
    def save(self, record: dict):
        return True

def run_db_operations(repo):
    repo.query("SELECT * FROM users")
    repo.fetch_all("SELECT * FROM logs")
    repo.save({"id": 1})
""",
                encoding="utf-8",
            )

            # Python: Response Envelope Function
            (src / "api.py").write_text(
                """\
def format_response(data=None, error=None, meta=None):
    return {
        "status": "error" if error else "success",
        "data": data,
        "error": error,
        "meta": meta or {"version": "1.0"}
    }
""",
                encoding="utf-8",
            )

            # TypeScript: Interface, Enum, Type Alias
            (src / "types.ts").write_text(
                """\
export interface ApiResponse<T> {
    status: string;
    data: T;
    error?: string;
    meta?: Record<string, any>;
}

export enum ErrorCode {
    FORBIDDEN = "ERR_FORBIDDEN",
    RATE_LIMITED = "ERR_RATE_LIMITED"
}

export type UserProfile = {
    id: string;
    role: string;
}
""",
                encoding="utf-8",
            )

            # TypeScript: Service using findMany
            (src / "client.ts").write_text(
                """\
export class ClientService {
    async fetchUsers(db: any) {
        return await db.findMany();
    }
}
""",
                encoding="utf-8",
            )

            # --- STEP 1: Discovery ---
            res_disc = _run(tmp, tmp / "scripts" / "discover_standards.py", ["--json"])
            self.assertEqual(
                res_disc.returncode,
                0,
                f"Discovery failed: {res_disc.stderr}\n{res_disc.stdout}",
            )
            disc_data = json.loads(res_disc.stdout)

            # Verify response envelope keys
            env_keys = set(disc_data.get("response_envelope", {}).keys())
            for expected_k in ("status", "data", "error", "meta"):
                self.assertIn(
                    expected_k,
                    env_keys,
                    f"Expected envelope key '{expected_k}' in {env_keys}",
                )

            # Verify error codes across Python and TypeScript
            disc_errs = set(disc_data.get("error_codes", []))
            for expected_err in (
                "ERR_BASE_APPLICATION",
                "ERR_UNAUTHORIZED",
                "ERR_NOT_FOUND",
                "ERR_FORBIDDEN",
                "ERR_RATE_LIMITED",
            ):
                self.assertIn(
                    expected_err,
                    disc_errs,
                    f"Expected error code '{expected_err}' in {disc_errs}",
                )

            # Verify schemas detected
            schemas = disc_data.get("schemas", {})
            self.assertIn("UserPayload", schemas)
            self.assertIn("ServerConfig", schemas)
            self.assertIn("ApiResponse", schemas)
            self.assertIn("UserProfile", schemas)

            # Verify database patterns detected
            db_pats = set(disc_data.get("database_patterns", []))
            for pat in ("query", "fetch_all", "save", "findMany"):
                self.assertIn(
                    pat,
                    db_pats,
                    f"Expected DB pattern '{pat}' in {db_pats}",
                )

            # Verify cache idempotency
            res_disc_cached = _run(tmp, tmp / "scripts" / "discover_standards.py", ["--json"])
            self.assertEqual(res_disc_cached.returncode, 0)
            cached_data = json.loads(res_disc_cached.stdout)
            self.assertEqual(cached_data["cache_sha256"], disc_data["cache_sha256"])

            # --- STEP 2: Spec Shaper with --from-standards ---
            res_shape = _run(
                tmp,
                tmp / "scripts" / "shape_spec.py",
                [
                    "--from-standards",
                    "--slug",
                    "polyglot-feature",
                    "--title",
                    "Polyglot Feature",
                    "--assert-file",
                    "src/app.py",
                ],
            )
            self.assertEqual(
                res_shape.returncode,
                0,
                f"Spec shaping failed: {res_shape.stderr}\n{res_shape.stdout}",
            )

            spec_dir = tmp / "specs" / "polyglot-feature"
            self.assertTrue((spec_dir / "SPEC.md").is_file())
            self.assertTrue((spec_dir / "VERIFICATION.json").is_file())

            spec_md = (spec_dir / "SPEC.md").read_text(encoding="utf-8")
            self.assertIn("Code adheres to discovered response envelope", spec_md)
            self.assertIn("Error handling adheres to declared error code standards", spec_md)
            self.assertIn("Database interactions follow approved query methods", spec_md)

            v_json = json.loads((spec_dir / "VERIFICATION.json").read_text(encoding="utf-8"))
            self.assertIn("src/app.py", v_json["assertions"]["files_exist"])
            self.assertIn(
                "python scripts/check_compliance.py --files src/app.py",
                v_json["assertions"]["commands"],
            )

            # --- STEP 3: Compliance Checking ---
            # 3a. Valid file adhering to all standards
            (src / "app.py").write_text(
                """\
class AppHandler:
    def handle_request(self, repo):
        repo.query("SELECT * FROM users")
        return {
            "status": "success",
            "data": {"id": 1, "username": "alice"},
            "error": None,
            "meta": {"processed": True}
        }

    def handle_error(self):
        code = "ERR_UNAUTHORIZED"
        return {
            "status": "error",
            "data": None,
            "error": code,
            "meta": {}
        }
""",
                encoding="utf-8",
            )

            res_comp_valid = _run(
                tmp,
                tmp / "scripts" / "check_compliance.py",
                ["--files", "src/app.py", "--json"],
            )
            self.assertEqual(
                res_comp_valid.returncode,
                0,
                f"Expected compliant file to pass: {res_comp_valid.stderr}\n{res_comp_valid.stdout}",
            )
            comp_valid_data = json.loads(res_comp_valid.stdout)
            self.assertTrue(comp_valid_data["compliant"])
            self.assertEqual(comp_valid_data["violations_count"], 0)

            # 3b. Invalid file violating error codes, response envelopes, and database patterns
            (src / "invalid_app.py").write_text(
                """\
class InvalidHandler:
    def execute_bad(self, repo):
        repo.raw_query("SELECT 1")
        err = "ERR_UNDECLARED_ROGUE_CODE"
        return {
            "status": "unsupported_status_val",
            "result": {"bad": True},
            "error": err
        }
""",
                encoding="utf-8",
            )

            res_comp_invalid = _run(
                tmp,
                tmp / "scripts" / "check_compliance.py",
                ["--files", "src/invalid_app.py", "--json"],
            )
            self.assertEqual(res_comp_invalid.returncode, 1)
            comp_invalid_data = json.loads(res_comp_invalid.stdout)
            self.assertFalse(comp_invalid_data["compliant"])
            rules_violated = {v["rule"] for v in comp_invalid_data["violations"]}
            self.assertIn("UNDECLARED_ERROR_CODE", rules_violated)
            self.assertIn("PROHIBITED_DB_METHOD", rules_violated)
            self.assertIn("MALFORMED_RESPONSE_ENVELOPE", rules_violated)

            # --- STEP 4: Verification Contract ---
            res_verify = _run(
                tmp,
                tmp / "scripts" / "verify_spec.py",
                ["--spec", "specs/polyglot-feature", "--json"],
            )
            self.assertEqual(
                res_verify.returncode,
                0,
                f"verify_spec failed: {res_verify.stderr}\n{res_verify.stdout}",
            )
            verify_data = json.loads(res_verify.stdout)
            self.assertEqual(verify_data.get("status"), "PASSED")

            # --- STEP 5: Reverse Indexing Lookups ---
            # Symbol search: Pydantic model
            res_sym_pydantic = _run(
                tmp,
                tmp / "scripts" / "index_standards.py",
                ["--query", "UserPayload", "--json"],
            )
            self.assertEqual(res_sym_pydantic.returncode, 0)
            pydantic_res = json.loads(res_sym_pydantic.stdout)
            self.assertTrue(
                any(
                    d["name"] == "UserPayload"
                    and d["kind"] == "pydantic_model"
                    and "models.py" in d["file"]
                    for d in pydantic_res
                )
            )

            # Symbol search: TypeScript Interface
            res_sym_ts = _run(
                tmp,
                tmp / "scripts" / "index_standards.py",
                ["--query", "ApiResponse", "--json"],
            )
            self.assertEqual(res_sym_ts.returncode, 0)
            ts_res = json.loads(res_sym_ts.stdout)
            self.assertTrue(
                any(
                    d["name"] == "ApiResponse"
                    and d["kind"] == "interface"
                    and "types.ts" in d["file"]
                    for d in ts_res
                )
            )

            # Error code search: Python exception code
            res_err_py = _run(
                tmp,
                tmp / "scripts" / "index_standards.py",
                ["--error-code", "ERR_UNAUTHORIZED", "--json"],
            )
            self.assertEqual(res_err_py.returncode, 0)
            err_py_res = json.loads(res_err_py.stdout)
            self.assertTrue(
                any(
                    d["error_code"] == "ERR_UNAUTHORIZED" and "errors.py" in d["file"]
                    for d in err_py_res
                )
            )

            # Error code search: TypeScript enum code
            res_err_ts = _run(
                tmp,
                tmp / "scripts" / "index_standards.py",
                ["--error-code", "ERR_FORBIDDEN", "--json"],
            )
            self.assertEqual(res_err_ts.returncode, 0)
            err_ts_res = json.loads(res_err_ts.stdout)
            self.assertTrue(
                any(
                    d["error_code"] == "ERR_FORBIDDEN" and "types.ts" in d["file"]
                    for d in err_ts_res
                )
            )

            # Negative search
            res_neg_sym = _run(
                tmp,
                tmp / "scripts" / "index_standards.py",
                ["--query", "NonExistentModel"],
            )
            self.assertEqual(res_neg_sym.returncode, 1)

            res_neg_err = _run(
                tmp,
                tmp / "scripts" / "index_standards.py",
                ["--error-code", "ERR_NON_EXISTENT"],
            )
            self.assertEqual(res_neg_err.returncode, 1)

    def test_malformed_syntax_and_binary_resilience(self):
        """Engine resilience when encountering malformed code, empty files, and binary files.

        Verifies:
        1. Discovery engine scans cleanly without crashing.
        2. Indexing engine processes without unhandled exceptions.
        3. Compliance checker captures syntax warnings or read errors gracefully.
        """
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _copy_scripts_to(tmp)
            src = tmp / "src"
            src.mkdir(parents=True, exist_ok=True)

            # 1. Invalid Python Syntax
            (src / "broken.py").write_text(
                """\
def broken_syntax(
    x = 1
class IncompleteClass(
""",
                encoding="utf-8",
            )

            # 2. Invalid TypeScript Syntax
            (src / "broken.ts").write_text(
                """\
export interface { {{ broken
const invalid = ;;;
""",
                encoding="utf-8",
            )

            # 3. Empty files
            (src / "empty.py").write_text("", encoding="utf-8")
            (src / "empty.ts").write_text("", encoding="utf-8")

            # 4. Binary content disguised as source files
            (src / "binary_data.py").write_bytes(
                b"\x00\xff\xfe\x01\x02\x03\x80\x81\xff\x00\x00\x00"
            )
            (src / "binary_blob.ts").write_bytes(
                b"\x7f\x45\x4c\x46\x02\x01\x01\x00\x00\x00\xff\xee"
            )

            # 5. One valid file
            (src / "valid.py").write_text(
                """\
class StableService:
    ERROR_CODE = "ERR_STABLE_SERVICE"
    def execute(self):
        return {
            "status": "success",
            "data": {"alive": True},
            "error": None
        }
""",
                encoding="utf-8",
            )

            # Test discover_standards on malformed/binary repo
            res_disc = _run(tmp, tmp / "scripts" / "discover_standards.py", ["--json"])
            self.assertEqual(
                res_disc.returncode,
                0,
                f"discover_standards crashed on malformed files: {res_disc.stderr}",
            )
            disc_data = json.loads(res_disc.stdout)
            self.assertIn("ERR_STABLE_SERVICE", disc_data.get("error_codes", []))

            # Test index_standards on malformed/binary repo
            res_index = _run(
                tmp,
                tmp / "scripts" / "index_standards.py",
                ["--query", "StableService", "--json"],
            )
            self.assertEqual(
                res_index.returncode,
                0,
                f"index_standards crashed on malformed repo: {res_index.stderr}",
            )
            idx_data = json.loads(res_index.stdout)
            self.assertTrue(any(d["name"] == "StableService" for d in idx_data))

            # Test check_compliance on malformed files directly
            res_comp = _run(
                tmp,
                tmp / "scripts" / "check_compliance.py",
                [
                    "--files",
                    "src/broken.py",
                    "src/empty.py",
                    "src/binary_data.py",
                    "src/valid.py",
                    "--json",
                ],
            )
            # Exit code can be 0 or 1 depending on whether broken syntax contains undeclared error tokens,
            # but it MUST be valid JSON output and NOT an unhandled Python traceback crash.
            self.assertNotIn("Traceback (most recent call last):", res_comp.stderr)
            report = json.loads(res_comp.stdout)
            self.assertIn("files_checked", report)
            # Verify warnings captured for syntax error / read error
            warnings = report.get("warnings", [])
            warning_files = [w.get("file", "") for w in warnings]
            self.assertTrue(
                any("broken.py" in f for f in warning_files)
                or any("binary_data.py" in f for f in warning_files)
            )

    def test_windows_unicode_and_special_characters(self):
        """Resilience when handling Arabic, Chinese, Japanese, emoji, and accented characters.

        Verifies all scripts run cleanly without UnicodeEncodeError/UnicodeDecodeError
        in file content, file paths, and CLI parameters.
        """
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            _copy_scripts_to(tmp)
            src = tmp / "src"
            src.mkdir(parents=True, exist_ok=True)

            # Python file with Arabic, Chinese, Japanese, accents, and emojis
            arabic_file = src / "مرحبا_service.py"
            arabic_file.write_text(
                """\
# -*- coding: utf-8 -*-
\"\"\"
وحدة اختبار دعم اللغات والرموز الخاصة: 🚀 ✨ 🔥
Contient des caractères accentués: résumé, naïve, münchen.
\"\"\"

class MultilingualService:
    \"\"\"خدمة متعددة اللغات 🌸\"\"\"
    ERROR_CODE = "ERR_UNICODE_SUPPORTED"

    def execute(self, query: str):
        # 日本語のコメント: データベースクエリを実行
        return []

    def respond(self):
        # 中文注释: 返回标准响应
        return {
            "status": "success",
            "data": {
                "greeting": "مرحبا بالعالم",
                "emoji": "🎉",
                "chinese": "你好世界",
                "japanese": "こんにちは世界"
            },
            "error": None,
            "meta": {"locale": "multilingual"}
        }
""",
                encoding="utf-8",
            )

            # TypeScript file with Japanese and emojis
            japanese_file = src / "こんにちは_types.ts"
            japanese_file.write_text(
                """\
// 日本語のインターフェース定義
export interface MultiLangResponse<T> {
    status: string;
    data: T;
    error?: string;
}

export enum MultiLangErrors {
    UNSUPPORTED = "ERR_LANG_UNSUPPORTED" // ⚠️ 未対応言語
}
""",
                encoding="utf-8",
            )

            # 1. discover_standards with unicode paths & contents
            res_disc = _run(tmp, tmp / "scripts" / "discover_standards.py", ["--json"])
            self.assertEqual(
                res_disc.returncode,
                0,
                f"discover_standards failed with unicode: {res_disc.stderr}",
            )
            disc_data = json.loads(res_disc.stdout)
            self.assertIn("ERR_UNICODE_SUPPORTED", disc_data.get("error_codes", []))
            self.assertIn("ERR_LANG_UNSUPPORTED", disc_data.get("error_codes", []))

            # 2. shape_spec with unicode title, criteria, and unicode file paths
            res_shape = _run(
                tmp,
                tmp / "scripts" / "shape_spec.py",
                [
                    "--from-standards",
                    "--slug",
                    "unicode-feature",
                    "--title",
                    "مرحبا 🚀 Unicode & Emojis",
                    "--criterion",
                    "يدعم الرموز التعبيرية 🌸 واللغات المختلفة",
                    "--assert-file",
                    "src/مرحبا_service.py",
                ],
            )
            self.assertEqual(
                res_shape.returncode,
                0,
                f"shape_spec failed with unicode: {res_shape.stderr}",
            )

            spec_dir = tmp / "specs" / "unicode-feature"
            spec_md = (spec_dir / "SPEC.md").read_text(encoding="utf-8")
            self.assertIn("مرحبا 🚀 Unicode & Emojis", spec_md)
            self.assertIn("يدعم الرموز التعبيرية 🌸 واللغات المختلفة", spec_md)

            # 3. check_compliance on unicode file path
            res_comp = _run(
                tmp,
                tmp / "scripts" / "check_compliance.py",
                ["--files", "src/مرحبا_service.py", "--json"],
            )
            self.assertEqual(
                res_comp.returncode,
                0,
                f"check_compliance failed with unicode: {res_comp.stderr}",
            )
            comp_data = json.loads(res_comp.stdout)
            self.assertTrue(comp_data["compliant"])

            # 4. verify_spec with unicode spec
            res_verify = _run(
                tmp,
                tmp / "scripts" / "verify_spec.py",
                ["--spec", "specs/unicode-feature", "--json"],
            )
            self.assertEqual(
                res_verify.returncode,
                0,
                f"verify_spec failed with unicode: {res_verify.stderr}",
            )
            verify_data = json.loads(res_verify.stdout)
            self.assertEqual(verify_data.get("status"), "PASSED")

            # 5. index_standards queries with unicode
            res_idx_sym = _run(
                tmp,
                tmp / "scripts" / "index_standards.py",
                ["--query", "MultilingualService", "--json"],
            )
            self.assertEqual(res_idx_sym.returncode, 0)
            idx_sym = json.loads(res_idx_sym.stdout)
            self.assertTrue(any(d["name"] == "MultilingualService" for d in idx_sym))

            res_idx_err = _run(
                tmp,
                tmp / "scripts" / "index_standards.py",
                ["--error-code", "ERR_UNICODE_SUPPORTED", "--json"],
            )
            self.assertEqual(res_idx_err.returncode, 0)
            idx_err = json.loads(res_idx_err.stdout)
            self.assertTrue(any(d["error_code"] == "ERR_UNICODE_SUPPORTED" for d in idx_err))

            # Text mode check (safe console printing of unicode)
            res_idx_text = _run(
                tmp,
                tmp / "scripts" / "index_standards.py",
                ["--query", "MultilingualService"],
            )
            self.assertEqual(res_idx_text.returncode, 0)
            self.assertIn("MultilingualService", res_idx_text.stdout)


if __name__ == "__main__":
    unittest.main()
