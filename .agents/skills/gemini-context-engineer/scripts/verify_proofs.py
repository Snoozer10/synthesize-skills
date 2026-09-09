import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_table_and_dag(content: str) -> dict:
    tasks = {}
    in_table = False

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("| ID |"):
            in_table = True
            continue

        if in_table and line.startswith("| :---"):
            continue

        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 4:
                task_id = parts[0].replace("`", "")
                status = parts[2]
                blocked_by_raw = parts[3]
                blocked_by = []
                if blocked_by_raw != "-":
                    blocked_by = [b.strip().replace("`", "") for b in blocked_by_raw.split(",")]

                proof_command = None
                if len(parts) >= 5:
                    proof_command = parts[4].strip("`") if parts[4].startswith("`") else parts[4]
                    if proof_command == "-":
                        proof_command = None

                tasks[task_id] = {
                    "id": task_id,
                    "status": status,
                    "blocked_by": blocked_by,
                    "proof_command": proof_command,
                }
        else:
            in_table = False

    return tasks


def update_status(content: str, task_id: str, new_status: str) -> str:
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("|") and f"`{task_id}`" in line.split("|")[1]:
            parts = [p.strip() for p in line.strip("|").split("|")]
            parts[2] = new_status
            lines[i] = "| " + " | ".join(parts) + " |"
            break
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workstream", help="Task ID to run proof for")
    parser.add_argument("--file", dest="context_file", help="Path to GEMINI.md")
    parser.add_argument("--context-file", dest="context_file", help="Path to GEMINI.md (alias)")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    parser.add_argument(
        "--check-only", action="store_true", help="Run proof without modifying file"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON matrix")
    args = parser.parse_args()

    if not args.context_file:
        parser.error("the following arguments are required: --file or --context-file")

    md_path = Path(args.context_file)
    content = md_path.read_text(encoding="utf-8")

    tasks = parse_table_and_dag(content)

    if args.json:
        print(json.dumps(tasks, indent=2))
        return

    if not args.workstream:
        return

    task_id = args.workstream
    if task_id not in tasks:
        sys.stderr.write(f"ERR_TASK_NOT_FOUND: {task_id}\n")
        sys.exit(1)

    task = tasks[task_id]

    for dep_id in task["blocked_by"]:
        if dep_id in tasks and tasks[dep_id]["status"] != "Done":
            sys.stderr.write(f"ERR_DEPENDENCY_BLOCKED: {task_id} blocked by {dep_id}\n")
            sys.exit(1)

    proof_cmd = task.get("proof_command")
    if not proof_cmd or proof_cmd == "-":
        sys.stderr.write(f"ERR_NO_PROOF_COMMAND: {task_id}\n")
        sys.exit(1)

    try:
        if sys.platform == "win32":
            result = subprocess.run(proof_cmd, shell=True, timeout=args.timeout)
        else:
            result = subprocess.run(
                proof_cmd, shell=True, executable="/bin/bash", timeout=args.timeout
            )
    except subprocess.TimeoutExpired:
        sys.stderr.write(f"ERR_PROOF_TIMEOUT: {task_id} timed out after {args.timeout}s\n")
        sys.exit(1)

    if result.returncode != 0:
        sys.stderr.write(f"ERR_PROOF_FAILED: {task_id}\n")
        sys.exit(1)

    if not args.check_only:
        new_content = update_status(content, task_id, "Done")

        tmp_path = md_path.with_suffix(".md.tmp")
        tmp_path.write_text(new_content, encoding="utf-8")
        tmp_path.replace(md_path)

        # Check if anything was unlocked
        unlocked = []
        for t_id, t_info in tasks.items():
            if task_id in t_info["blocked_by"]:
                unlocked.append(t_id)
        if unlocked:
            print(f"Task {task_id} unlocked: {', '.join(unlocked)}")


if __name__ == "__main__":
    main()
