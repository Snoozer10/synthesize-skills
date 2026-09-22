#!/usr/bin/env python3
"""
scripts/detect_hosts.py — Cross-Agent Host Detection & Target Directory Resolver
Stdlib only. Detects installed AI agent platforms and maps target directories.
"""
import json
import os
import sys
from pathlib import Path


def get_home_dir() -> Path:
    """Return user home directory in a platform-independent manner."""
    return Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or Path.home()).resolve()


HOST_DEFINITIONS = {
    "antigravity": {
        "name": "Google Antigravity / Gemini CLI",
        "env_vars": ["ANTIGRAVITY_AGENT", "GEMINI_CLI"],
        "home_paths": [".gemini/antigravity-cli", ".gemini/antigravity", ".gemini"],
        "project_skills": ".gemini/skills",
        "global_skills": [".gemini/skills", ".gemini/antigravity-cli/skills"],
        "project_rules": ".gemini/rules",
    },
    "claude": {
        "name": "Claude Code / Claude CLI",
        "env_vars": ["CLAUDECODE", "CLAUDE_CODE"],
        "home_paths": [".claude"],
        "project_skills": ".claude/skills",
        "global_skills": [".claude/skills"],
        "project_commands": ".claude/commands",
    },
    "codex": {
        "name": "OpenAI Codex CLI / Desktop",
        "env_vars": ["CODEX_SANDBOX", "CODEX_THREAD_ID", "CODEX_CI"],
        "home_paths": [".codex"],
        "project_skills": ".codex/skills",
        "global_skills": [".codex/skills"],
        "project_rules": ".codex/rules",
    },
    "opencode": {
        "name": "OpenCode",
        "env_vars": ["OPENCODE_CLIENT"],
        "home_paths": [".config/opencode", ".opencode"],
        "project_skills": ".opencode/skills",
        "global_skills": [".config/opencode/skills", ".opencode/skills"],
        "project_commands": ".opencode/commands",
    },
    "cursor": {
        "name": "Cursor Editor & Agent",
        "env_vars": ["CURSOR_TRACE_ID", "CURSOR_AGENT"],
        "home_paths": [".cursor"],
        "project_skills": ".cursor/skills",
        "global_skills": [".cursor/skills"],
        "project_rules": ".cursor/rules",
    },
    "windsurf": {
        "name": "Codeium Windsurf",
        "env_vars": [],
        "home_paths": [".codeium/windsurf"],
        "project_skills": ".windsurf/skills",
        "global_skills": [".codeium/windsurf/skills"],
        "project_rules": ".windsurf/rules",
    },
    "copilot": {
        "name": "GitHub Copilot CLI / Extension",
        "env_vars": ["COPILOT_MODEL", "COPILOT_ALLOW_ALL"],
        "home_paths": [".copilot"],
        "project_skills": ".copilot/skills",
        "global_skills": [".copilot/skills"],
        "project_rules": ".github",
    },
    "agents": {
        "name": "Open Agents Standard (Canonical SSOT)",
        "env_vars": [],
        "home_paths": [".agents"],
        "project_skills": ".agents/skills",
        "global_skills": [".agents/skills"],
        "project_rules": "AGENTS.md",
    },
}


def detect_hosts(project_root: Path = None) -> dict:
    """Audit system environment and directories to discover active/installed AI hosts."""
    if project_root is None:
        project_root = Path(".").resolve()
    home = get_home_dir()

    results = {}
    for host_id, defn in HOST_DEFINITIONS.items():
        detected = False
        detection_reasons = []

        # 1. Probe Environment Variables
        for ev in defn["env_vars"]:
            if os.environ.get(ev):
                detected = True
                detection_reasons.append(f"env:{ev}")

        # 2. Probe Home Directory Paths
        for rel_hp in defn["home_paths"]:
            full_hp = home / rel_hp
            if full_hp.exists():
                detected = True
                detection_reasons.append(f"home_dir:{rel_hp}")

        # 3. Probe Project Directory Paths
        proj_skill = project_root / defn["project_skills"]
        if proj_skill.exists():
            detected = True
            detection_reasons.append(f"project_dir:{defn['project_skills']}")

        # Canonical .agents always exists as universal fallback
        if host_id == "agents":
            detected = True
            if "default:universal" not in detection_reasons:
                detection_reasons.append("default:universal")

        # Resolve primary global install dir
        primary_global = str(home / defn["global_skills"][0])
        primary_project = str(project_root / defn["project_skills"])

        results[host_id] = {
            "name": defn["name"],
            "detected": detected,
            "reasons": detection_reasons,
            "project_skills_path": defn["project_skills"],
            "project_skills_abs": primary_project,
            "global_skills_abs": primary_global,
        }

    return results


def main(argv):
    import argparse
    parser = argparse.ArgumentParser(description="Detect installed AI agent hosts.")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    parser.add_argument("--all", action="store_true", help="List all hosts including undetected")
    parser.add_argument("--stage-dir", type=str, help="Optional staging directory to write receipt to")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed detection reasons")
    args = parser.parse_args(argv[1:])

    hosts = detect_hosts()

    if args.stage_dir:
        stage = Path(args.stage_dir)
        stage.mkdir(parents=True, exist_ok=True)
        receipt = stage / "host_inventory_receipt.json"
        receipt.write_text(json.dumps(hosts, indent=2) + "\n", encoding="utf-8")
        if not args.json:
            print(f"Wrote host inventory receipt to: {receipt}")

    if args.json:
        print(json.dumps(hosts, indent=2))
        return 0

    print("=== AI Agent Host Detection Audit ===")
    detected_count = 0
    for hid, info in hosts.items():
        if info["detected"] or args.all:
            if info["detected"]:
                detected_count += 1
                status = "[ACTIVE/INSTALLED]"
            else:
                status = "[NOT FOUND]"
            print(f"\n{status} {hid.upper()} — {info['name']}")
            print(f"  Project Target: {info['project_skills_path']}")
            print(f"  Global Target:  {info['global_skills_abs']}")
            if args.verbose and info["reasons"]:
                print(f"  Signals:        {', '.join(info['reasons'])}")

    print(f"\nTotal Detected Hosts: {detected_count} / {len(hosts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
