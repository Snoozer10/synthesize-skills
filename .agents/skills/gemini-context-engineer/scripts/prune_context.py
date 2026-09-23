#!/usr/bin/env python3
"""
scripts/prune_context.py — Context Decomposition & Sharding Engine

Deterministically shards non-conforming spec dumps, completed workstreams,
excess failure modes, and historical session archives to structured files
under docs/, leaving behind standardized single-line alert pointers and
reporting line/byte/token metrics before and after.

Python standard library only.
"""

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add script directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))
from __version__ import __version__

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

CANONICAL_H2S = [
    "## 🎯 Project Overview",
    "## 🏗️ Architecture & Component Mapping",
    "## 🛑 Mandatory Engineering Constraints",
    "## 🛠️ Common Workflows & CLI Commands",
    "## 🔄 Active Workstreams & Verification Status",
]


def strip_variation_selectors(text: str) -> str:
    return text.replace("\ufe0f", "")


CANONICAL_H2_SET = {
    strip_variation_selectors(h2).strip() for h2 in CANONICAL_H2S
}

INVARIANT_PATTERN = re.compile(
    r"\b(MUST|NEVER|ALWAYS|filter_complex|no\s+DNS)\b",
    re.IGNORECASE,
)


def slugify(title: str) -> str:
    s = title.strip()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    if slug.startswith("adaptive-multi-channel-production"):
        return "adaptive-production"
    return slug or "spec"


def calculate_metrics(content: str) -> dict:
    return {
        "lines": len(content.splitlines()),
        "bytes": len(content.encode("utf-8")),
        "tokens": len(content) // 4,
    }


def calculate_deltas(before: dict, after: dict) -> dict:
    def pct(b, a):
        if b == 0:
            return 0.0
        return round(((b - a) / b) * 100, 1)

    return {
        "delta_lines_pct": pct(before["lines"], after["lines"]),
        "delta_bytes_pct": pct(before["bytes"], after["bytes"]),
        "delta_tokens_pct": pct(before["tokens"], after["tokens"]),
    }


def format_metrics_table(stats_before: dict, stats_after: dict, file_label: str) -> str:
    deltas = calculate_deltas(stats_before, stats_after)
    lines_b = f"{stats_before['lines']:,}"
    lines_a = f"{stats_after['lines']:,}"
    lines_pct = f"{deltas['delta_lines_pct']:.1f}%"

    bytes_b = f"{stats_before['bytes']:,} B"
    bytes_a = f"{stats_after['bytes']:,} B"
    bytes_pct = f"{deltas['delta_bytes_pct']:.1f}%"

    tokens_b = f"{stats_before['tokens']:,}"
    tokens_a = f"{stats_after['tokens']:,}"
    tokens_pct = f"{deltas['delta_tokens_pct']:.1f}%"

    title = f"Context Pruning Metrics: {file_label}"
    width = 62
    border_top = f"┌{'─' * width}┐"
    border_mid = f"├{'─' * 14}┬{'─' * 14}┬{'─' * 14}┬{'─' * 16}┤"
    border_bot = f"└{'─' * 14}┴{'─' * 14}┴{'─' * 14}┴{'─' * 16}┘"

    header_row = f"│ {'Metric':<12} │ {'Before':<12} │ {'After':<12} │ {'Reduction %':<14} │"
    row1 = f"│ {'Lines':<12} │ {lines_b:<12} │ {lines_a:<12} │ {lines_pct:<14} │"
    row2 = f"│ {'Bytes':<12} │ {bytes_b:<12} │ {bytes_a:<12} │ {bytes_pct:<14} │"
    row3 = f"│ {'Tokens':<12} │ {tokens_b:<12} │ {tokens_a:<12} │ {tokens_pct:<14} │"

    return "\n".join([
        border_top,
        f"│ {title:<{width - 1}}│",
        border_mid,
        header_row,
        border_mid,
        row1,
        row2,
        row3,
        border_bot,
    ])


def rotate_backups(filepath: Path, max_backups: int = 3):
    if not filepath.exists():
        return
    bak_pattern = f"{filepath.name}.*.bak"
    backups = sorted(filepath.parent.glob(bak_pattern))
    while len(backups) >= max_backups:
        oldest = backups.pop(0)
        oldest.unlink(missing_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    new_bak = filepath.parent / f"{filepath.name}.{ts}.bak"
    shutil.copy2(filepath, new_bak)


def atomic_write_text(filepath: Path, content: str, encoding: str = "utf-8"):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=filepath.parent, delete=False, encoding=encoding) as tf:
        tf.write(content)
        tf.flush()
        os.fsync(tf.fileno())
        temp_name = tf.name
    os.replace(temp_name, filepath)


def extract_invariants_from_text(text: str) -> list[str]:
    invariants = []
    lines = text.splitlines()
    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line:
            continue
        # Strip leading bullet/list markers
        content_line = re.sub(r"^[-*+]\s+", "", cleaned_line)
        content_line = re.sub(r"^\d+\.\s+", "", content_line)

        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", content_line)
        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            if INVARIANT_PATTERN.search(s_clean):
                invariants.append(s_clean)
    return invariants


def update_frontmatter_last_indexed(content: str) -> str:
    today_str = datetime.now().strftime("%Y-%m-%d")
    if content.startswith("---\n") or content.startswith("---\r\n"):
        delimiter = "\r\n" if "\r\n" in content[:10] else "\n"
        parts = content.split(f"---{delimiter}", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            if re.search(r"^last_indexed:\s*.*$", fm_text, re.MULTILINE):
                fm_text = re.sub(
                    r"^last_indexed:\s*.*$",
                    f'last_indexed: "{today_str}"',
                    fm_text,
                    flags=re.MULTILINE,
                )
            else:
                if not fm_text.endswith("\n"):
                    fm_text += "\n"
                fm_text += f'last_indexed: "{today_str}"\n'
            return f"---{delimiter}{fm_text}---{delimiter}{parts[2]}"
    return content


def prune_gemini_md(
    content: str, repo_root: Path, keep_learnings: int = 7, dry_run: bool = False
) -> tuple[str, dict]:
    stats_before = calculate_metrics(content)
    sharded_files = []
    extracted_invariants = []

    # Update frontmatter last_indexed
    content = update_frontmatter_last_indexed(content)

    # 1. Split content into sections based on H2 headers
    # Find all '^## ' lines
    lines = content.splitlines(keepends=True)
    h2_indices = []
    for idx, line in enumerate(lines):
        if line.startswith("## "):
            h2_indices.append(idx)

    sections = []
    # Preamble before first H2
    first_h2 = h2_indices[0] if h2_indices else len(lines)
    preamble = "".join(lines[:first_h2])

    for i, start_idx in enumerate(h2_indices):
        end_idx = h2_indices[i + 1] if i + 1 < len(h2_indices) else len(lines)
        header_line = lines[start_idx].strip()
        header_title = header_line[3:].strip()
        section_text = "".join(lines[start_idx:end_idx])
        body_text = "".join(lines[start_idx + 1 : end_idx])

        norm_h2 = strip_variation_selectors(header_line).strip()
        is_canonical = norm_h2 in CANONICAL_H2_SET

        sections.append({
            "header_line": header_line,
            "header_title": header_title,
            "norm_h2": norm_h2,
            "is_canonical": is_canonical,
            "section_text": section_text,
            "body_text": body_text,
        })

    # 2. Identify rogue sections and extract invariants / shard content
    rogue_sections = [s for s in sections if not s["is_canonical"]]
    canonical_sections = [s for s in sections if s["is_canonical"]]

    # Collect invariants from rogue sections
    for rs in rogue_sections:
        invs = extract_invariants_from_text(rs["section_text"])
        for inv in invs:
            if inv not in extracted_invariants:
                extracted_invariants.append(inv)

        # Write sharded spec file
        slug = slugify(rs["header_title"])
        spec_rel = f"docs/specs/{slug}.md"
        spec_path = repo_root / "docs" / "specs" / f"{slug}.md"
        sharded_files.append(spec_rel)

        if not dry_run:
            today_str = datetime.now().strftime("%Y-%m-%d")
            spec_content = (
                f"# {rs['header_title']}\n\n"
                f"> **Source:** Sharded from GEMINI.md\n"
                f"> **Date:** {today_str}\n\n"
                f"{rs['body_text'].strip()}\n"
            )
            atomic_write_text(spec_path, spec_content)

    # 3. Locate Section 3 (## 🛑 Mandatory Engineering Constraints) and inject invariants
    sec3 = None
    for s in canonical_sections:
        if "Mandatory Engineering Constraints" in s["header_line"]:
            sec3 = s
            break

    if sec3 and extracted_invariants:
        sec3_text = sec3["section_text"]
        new_bullets = []
        for inv in extracted_invariants:
            # Deduplicate against existing text in Section 3
            if inv.lower() not in sec3_text.lower():
                new_bullets.append(f"- {inv}")

        if new_bullets:
            inv_block = "\n".join(new_bullets) + "\n"
            target_sub = "### Technical & Environmental Invariants"
            if target_sub in sec3_text:
                parts = sec3_text.split(target_sub, 1)
                sub_heading = parts[0] + target_sub + "\n"
                sub_rest = parts[1]
                # Insert at the beginning or end of Technical & Environmental Invariants
                # Let's find end of the subsection (next '### ' or end of section)
                next_h3 = re.search(r"\n(?=### |\Z)", sub_rest)
                if next_h3:
                    insert_pos = next_h3.start()
                    sec3_updated = (
                        sub_heading
                        + sub_rest[:insert_pos].rstrip()
                        + "\n"
                        + inv_block
                        + sub_rest[insert_pos:]
                    )
                else:
                    sec3_updated = sub_heading + sub_rest.rstrip() + "\n" + inv_block
            else:
                sec3_updated = (
                    sec3_text.rstrip()
                    + f"\n\n### Technical & Environmental Invariants\n{inv_block}"
                )
            sec3["section_text"] = sec3_updated

    # 4. Process Section 5 (## 🔄 Active Workstreams & Verification Status)
    sec5 = None
    for s in canonical_sections:
        if "Active Workstreams & Verification Status" in s["header_line"]:
            sec5 = s
            break

    archived_workstreams_count = 0
    if sec5:
        sec5_text = sec5["section_text"]
        # Parse table rows in Section 5
        sec5_lines = sec5_text.splitlines()
        table_start = -1
        table_end = -1
        header_row_idx = -1
        separator_row_idx = -1
        data_rows = []

        for idx, line in enumerate(sec5_lines):
            stripped = line.strip()
            if stripped.startswith("### "):
                break
            if stripped.startswith("|") and stripped.endswith("|"):
                if table_start == -1:
                    table_start = idx
                    header_row_idx = idx
                elif separator_row_idx == -1 and ("---" in stripped or ":---" in stripped):
                    separator_row_idx = idx
                else:
                    data_rows.append(stripped)
                table_end = idx

        if table_start != -1 and separator_row_idx != -1:
            header_row = sec5_lines[header_row_idx]
            separator_row = sec5_lines[separator_row_idx]

            # Determine Status column index
            header_cells = [c.strip() for c in header_row.split("|")[1:-1]]
            status_col = 2
            for col_idx, col_name in enumerate(header_cells):
                if col_name.lower() == "status":
                    status_col = col_idx
                    break

            active_rows = []
            done_rows = []

            for row in data_rows:
                stripped_row = row.strip()
                if not stripped_row or "*No active workstreams*" in stripped_row:
                    continue
                cells = [c.strip() for c in stripped_row.split("|")[1:-1]]
                if len(cells) > status_col:
                    status_val = cells[status_col].lower()
                    if status_val.startswith("done"):
                        done_rows.append(stripped_row)
                    else:
                        active_rows.append(stripped_row)
                else:
                    active_rows.append(stripped_row)

            if done_rows:
                archived_workstreams_count = len(done_rows)
                workstream_rel = "docs/workstreams/archive.md"
                workstream_path = repo_root / "docs" / "workstreams" / "archive.md"
                sharded_files.append(workstream_rel)

                if not dry_run:
                    existing_archive = ""
                    if workstream_path.exists():
                        existing_archive = workstream_path.read_text(encoding="utf-8")

                    if not existing_archive.strip():
                        archive_content = (
                            "# Workstream Archive\n\n"
                            f"{header_row}\n"
                            f"{separator_row}\n"
                            + "\n".join(done_rows)
                            + "\n"
                        )
                        atomic_write_text(workstream_path, archive_content)
                    else:
                        # Append new rows not already in archive
                        new_rows_to_add = [
                            r for r in done_rows if r not in existing_archive
                        ]
                        if new_rows_to_add:
                            updated_archive = existing_archive.rstrip() + "\n" + "\n".join(new_rows_to_add) + "\n"
                            atomic_write_text(workstream_path, updated_archive)

                # Reconstruct Section 5 table
                new_table_lines = [header_row, separator_row]
                if active_rows:
                    new_table_lines.extend(active_rows)
                else:
                    new_table_lines.append("| - | *No active workstreams* | - | - | - |")

                # Pointer note for archived workstreams
                pointer_note = (
                    f"> [!NOTE]\n"
                    f"> {archived_workstreams_count} completed workstreams archived to [{workstream_rel}]({workstream_rel})."
                )

                # Rebuild sec5 lines
                before_table = sec5_lines[:table_start]
                after_table = sec5_lines[table_end + 1 :]

                # Check if existing archive pointer note is present in after_table
                after_table_text = "\n".join(after_table)
                after_table_text = re.sub(
                    r"> \[!NOTE\]\s*\n>\s*\d+\s+completed workstreams archived to \[docs/workstreams/archive\.md\]\(docs/workstreams/archive\.md\)\.\s*\n*",
                    "",
                    after_table_text,
                )

                sec5_text = (
                    "\n".join(before_table).rstrip()
                    + "\n"
                    + "\n".join(new_table_lines)
                    + "\n\n"
                    + pointer_note
                    + "\n\n"
                    + after_table_text.lstrip()
                )

        # 5. Failure Mode Compaction in Section 5
        learning_pattern = re.compile(r"^[-*+]\s+\[LEARNING-\d+\]:", re.MULTILINE)
        if learning_pattern.search(sec5_text):
            lines_sec5 = sec5_text.splitlines(keepends=True)
            learning_blocks = []
            current_block = []
            in_learnings = False
            first_learning_idx = -1
            last_learning_idx = -1

            for idx, line in enumerate(lines_sec5):
                stripped = line.strip()
                if re.match(r"^[-*+]\s+\[LEARNING-\d+\]:", stripped):
                    if not in_learnings:
                        in_learnings = True
                        first_learning_idx = idx
                    if current_block:
                        learning_blocks.append("".join(current_block))
                        current_block = []
                    current_block.append(line)
                    last_learning_idx = idx
                elif in_learnings:
                    if stripped.startswith("### ") or stripped.startswith("## ") or stripped.startswith("> [!NOTE]"):
                        in_learnings = False
                        if current_block:
                            learning_blocks.append("".join(current_block))
                            current_block = []
                    else:
                        current_block.append(line)
                        last_learning_idx = idx

            if current_block:
                learning_blocks.append("".join(current_block))

            if len(learning_blocks) > keep_learnings:
                errors_rel = "docs/error-solving/understood-errors.md"
                errors_path = repo_root / "docs" / "error-solving" / "understood-errors.md"
                sharded_files.append(errors_rel)

                if not dry_run:
                    existing_errors = ""
                    if errors_path.exists():
                        existing_errors = errors_path.read_text(encoding="utf-8")

                    full_catalog_text = "".join(learning_blocks)
                    if not existing_errors.strip():
                        errors_content = (
                            "# Understood Errors & Failure Modes\n\n"
                            "## Known Failure Modes & Learnings\n\n"
                            f"{full_catalog_text}\n"
                        )
                        atomic_write_text(errors_path, errors_content)
                    else:
                        # Append any learnings not yet in understood-errors.md
                        new_learnings = []
                        for lb in learning_blocks:
                            m_id = re.search(r"\[(LEARNING-\d+)\]", lb)
                            if m_id and m_id.group(1) not in existing_errors:
                                new_learnings.append(lb)
                            elif not m_id and lb not in existing_errors:
                                new_learnings.append(lb)

                        if new_learnings:
                            updated_errors = (
                                existing_errors.rstrip()
                                + "\n\n## Known Failure Modes & Learnings\n\n"
                                + "".join(new_learnings)
                            )
                            atomic_write_text(errors_path, updated_errors)

                # Keep top keep_learnings in sec5
                kept_blocks = learning_blocks[:keep_learnings]
                learnings_pointer = (
                    "> [!NOTE]\n"
                    f"> Complete catalog of failure modes and mitigation patterns indexed in [{errors_rel}]({errors_rel})."
                )

                before_learnings = "".join(lines_sec5[:first_learning_idx])
                after_learnings = "".join(lines_sec5[last_learning_idx + 1 :])

                # Clean any previous note in after_learnings
                after_learnings = re.sub(
                    r"> \[!NOTE\]\s*\n>\s*Complete catalog of failure modes and mitigation patterns indexed in \[docs/error-solving/understood-errors\.md\]\(docs/error-solving/understood-errors\.md\)\.\s*\n*",
                    "",
                    after_learnings,
                )

                sec5_text = (
                    before_learnings.rstrip()
                    + "\n"
                    + "".join(kept_blocks).rstrip()
                    + "\n\n"
                    + learnings_pointer
                    + "\n\n"
                    + after_learnings.lstrip()
                )

        sec5["section_text"] = sec5_text

    # 6. Reassemble pruned GEMINI.md
    # For rogue sections, leave pointer note under Section 2 or at the removal location
    # Build pointers for rogue sections
    rogue_pointers = []
    for rs in rogue_sections:
        slug = slugify(rs["header_title"])
        spec_rel = f"docs/specs/{slug}.md"
        ptr = (
            f"> [!NOTE]\n"
            f"> {rs['header_title']} specification sharded to [{spec_rel}]({spec_rel})."
        )
        rogue_pointers.append(ptr)

    # Reconstruct body preserving canonical order: Section 1, Section 2, Section 3, Section 4, Section 5
    # Pointer notes placed at removal location or under Section 2
    sec1 = next((s for s in canonical_sections if "Project Overview" in s["header_line"]), None)
    sec2 = next((s for s in canonical_sections if "Architecture & Component Mapping" in s["header_line"]), None)
    sec4 = next((s for s in canonical_sections if "Common Workflows & CLI Commands" in s["header_line"]), None)

    assembled_parts = [preamble.rstrip()]
    if sec1:
        assembled_parts.append(sec1["section_text"].rstrip())

    # If rogue sections existed, insert pointers
    if rogue_pointers:
        assembled_parts.append("\n\n".join(rogue_pointers))

    if sec2:
        assembled_parts.append(sec2["section_text"].rstrip())
    if sec3:
        assembled_parts.append(sec3["section_text"].rstrip())
    if sec4:
        assembled_parts.append(sec4["section_text"].rstrip())
    if sec5:
        assembled_parts.append(sec5["section_text"].rstrip())

    pruned_content = "\n\n".join(p for p in assembled_parts if p.strip()) + "\n"
    stats_after = calculate_metrics(pruned_content)
    deltas = calculate_deltas(stats_before, stats_after)

    result = {
        "stats_before": stats_before,
        "stats_after": stats_after,
        "delta_lines_pct": deltas["delta_lines_pct"],
        "delta_bytes_pct": deltas["delta_bytes_pct"],
        "delta_tokens_pct": deltas["delta_tokens_pct"],
        "sharded_files": sorted(list(set(sharded_files))),
        "extracted_invariants_count": len(extracted_invariants),
        "archived_workstreams_count": archived_workstreams_count,
    }
    return pruned_content, result


def prune_continuity_md(
    content: str, repo_root: Path, dry_run: bool = False
) -> tuple[str, dict]:
    stats_before = calculate_metrics(content)
    sharded_files = []

    lines = content.splitlines(keepends=True)
    archive_start = -1
    archive_end = -1
    archive_indent = ""

    # Locate - Historical Archive:
    for idx, line in enumerate(lines):
        m = re.match(r"^(\s*)-\s+Historical Archive:\s*$", line)
        if m:
            archive_start = idx
            archive_indent = m.group(1)
            break

    archived_milestones_count = 0
    if archive_start != -1:
        # Find all lines belonging to the archive
        archive_lines = []
        canonical_boundary = re.compile(
            r"^\s*-\s+(Goal|Constraints|Key decisions|State|Done|Now|Next|Open questions|Working set):",
            re.IGNORECASE,
        )

        idx = archive_start + 1
        while idx < len(lines):
            line = lines[idx]
            stripped = line.strip()
            # If line is another canonical section or header or separator
            if canonical_boundary.match(line) or line.startswith("## ") or line.startswith("---"):
                break
            if stripped:
                archive_lines.append(line)
            idx += 1
        archive_end = idx

        if archive_lines:
            archived_milestones_count = len(archive_lines)
            archive_rel = "docs/sessions/history/archive.md"
            archive_path = repo_root / "docs" / "sessions" / "history" / "archive.md"
            sharded_files.append(archive_rel)

            if not dry_run:
                existing_history = ""
                if archive_path.exists():
                    existing_history = archive_path.read_text(encoding="utf-8")

                milestones_text = "".join(archive_lines)
                if not existing_history.strip():
                    history_content = (
                        "# Session History Archive\n\n"
                        f"{milestones_text}\n"
                    )
                    atomic_write_text(archive_path, history_content)
                else:
                    new_history = existing_history.rstrip() + "\n\n" + milestones_text
                    atomic_write_text(archive_path, new_history)

            # Replacement block
            nested_indent = archive_indent + "  "
            replacement = (
                f"{archive_indent}- Historical Archive:\n"
                f"{nested_indent}- Past session milestones archived to [{archive_rel}]({archive_rel}).\n"
            )

            pruned_content = (
                "".join(lines[:archive_start])
                + replacement
                + "".join(lines[archive_end:])
            )
        else:
            pruned_content = content
    else:
        pruned_content = content

    stats_after = calculate_metrics(pruned_content)
    deltas = calculate_deltas(stats_before, stats_after)

    result = {
        "stats_before": stats_before,
        "stats_after": stats_after,
        "delta_lines_pct": deltas["delta_lines_pct"],
        "delta_bytes_pct": deltas["delta_bytes_pct"],
        "delta_tokens_pct": deltas["delta_tokens_pct"],
        "sharded_files": sorted(list(set(sharded_files))),
        "archived_milestones_count": archived_milestones_count,
    }
    return pruned_content, result


def main():
    parser = argparse.ArgumentParser(
        description="Deterministic context decomposition and sharding engine."
    )
    parser.add_argument(
        "--file", help="Target file to prune (e.g. GEMINI.md or CONTINUITY.md)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Prune both GEMINI.md and CONTINUITY.md in repo root",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Display metrics and diff without mutating disk",
    )
    parser.add_argument("--apply", action="store_true", help="Apply changes to disk")
    parser.add_argument(
        "--keep-learnings",
        type=int,
        default=7,
        help="Number of learnings to retain in GEMINI.md (default: 7)",
    )
    parser.add_argument(
        "--root", default=".", help="Repository root path (default: .)"
    )
    parser.add_argument(
        "--json", action="store_true", help="Print JSON metrics payload"
    )

    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    dry_run = not args.apply

    targets = []
    if args.all:
        gemini_candidate = repo_root / "GEMINI.md"
        continuity_candidate = repo_root / "CONTINUITY.md"
        if gemini_candidate.exists():
            targets.append(gemini_candidate)
        if continuity_candidate.exists():
            targets.append(continuity_candidate)
    elif args.file:
        fpath = Path(args.file)
        if not fpath.is_absolute():
            fpath = (repo_root / fpath).resolve()
        targets.append(fpath)
    else:
        # Default to checking root files
        gemini_candidate = repo_root / "GEMINI.md"
        if gemini_candidate.exists():
            targets.append(gemini_candidate)

    if not targets:
        print("No target files found to prune.", file=sys.stderr)
        sys.exit(1)

    json_payload = {"files": []}

    for target in targets:
        if not target.exists():
            print(f"Error: File not found: {target}", file=sys.stderr)
            continue

        raw_content = target.read_text(encoding="utf-8")
        is_gemini = (
            target.name.upper() == "GEMINI.MD"
            or "## 🎯" in raw_content
            or "Project Context" in raw_content
        )

        file_repo_root = repo_root
        if args.root == "." and not target.is_relative_to(repo_root):
            file_repo_root = target.parent

        if is_gemini:
            pruned, res = prune_gemini_md(
                raw_content,
                file_repo_root,
                keep_learnings=args.keep_learnings,
                dry_run=dry_run,
            )
        else:
            pruned, res = prune_continuity_md(
                raw_content, file_repo_root, dry_run=dry_run
            )

        if not dry_run:
            rotate_backups(target)
            atomic_write_text(target, pruned)

        try:
            rel_label = str(target.relative_to(file_repo_root)).replace("\\", "/")
        except ValueError:
            rel_label = target.name

        file_payload = {
            "file": rel_label,
            "stats_before": res["stats_before"],
            "stats_after": res["stats_after"],
            "delta_lines_pct": res["delta_lines_pct"],
            "delta_bytes_pct": res["delta_bytes_pct"],
            "delta_tokens_pct": res["delta_tokens_pct"],
            "sharded_files": res["sharded_files"],
        }
        json_payload["files"].append(file_payload)

        if not args.json:
            table_str = format_metrics_table(
                res["stats_before"], res["stats_after"], target.name
            )
            print(table_str)
            if res["sharded_files"]:
                print(f"  Sharded files ({len(res['sharded_files'])}):")
                for sf in res["sharded_files"]:
                    print(f"    - {sf}")
            if dry_run:
                print("  [DRY RUN] No disk files were mutated.")
            else:
                print(f"  [APPLIED] Updated {target.name} and rotated backups.")
            print()

    if args.json:
        print(json.dumps(json_payload, indent=2))


if __name__ == "__main__":
    main()
