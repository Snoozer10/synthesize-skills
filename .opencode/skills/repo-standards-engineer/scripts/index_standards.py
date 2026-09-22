"""Standards Indexer engine. Stdlib only.

Indexes symbols, error codes, response envelopes, and query methods
to their defining source files and line numbers with SHA-256 caching.
"""
import argparse
import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
try:
    from discover_standards import discover_standards, compute_tree_sha256
except ImportError:
    from .discover_standards import discover_standards, compute_tree_sha256


def build_standards_index(root: Path, force: bool = False) -> dict:
    runtime_dir = root / ".runtime"
    index_file = runtime_dir / "standards_index.json"

    tree_hash, target_files = compute_tree_sha256(root)

    if not force and index_file.is_file():
        try:
            cached = json.loads(index_file.read_text(encoding="utf-8"))
            if cached.get("cache_sha256") == tree_hash:
                return cached
        except Exception:
            pass

    standards = discover_standards(root, force=force)
    symbol_map = {}

    for f in target_files:
        rel = str(f.relative_to(root))
        if f.suffix.lower() == ".py":
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbol_map[f"def:{node.name}"] = {"file": rel, "line": node.lineno}
                    elif isinstance(node, ast.ClassDef):
                        symbol_map[f"class:{node.name}"] = {"file": rel, "line": node.lineno}
            except Exception:
                pass

    index_data = {
        "cache_sha256": tree_hash,
        "standards": standards,
        "symbols": symbol_map,
        "indexed_files": len(target_files)
    }

    try:
        runtime_dir.mkdir(parents=True, exist_ok=True)
        index_file.write_text(json.dumps(index_data, indent=2), encoding="utf-8")
    except Exception:
        pass

    return index_data


def main():
    parser = argparse.ArgumentParser(description="Index codebase standards and symbols.")
    parser.add_argument("--dir", default=".", help="Project directory to index")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--force", action="store_true", help="Bypass cache")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    idx = build_standards_index(root, force=args.force)

    if args.json:
        print(json.dumps(idx, indent=2))
    else:
        print(f"Standards Index Built (Hash: {idx['cache_sha256'][:8]}):")
        print(f"- Files indexed: {idx['indexed_files']}")
        print(f"- Discovered symbols: {len(idx['symbols'])}")
        print(f"- Error codes: {len(idx['standards'].get('error_codes', []))}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
