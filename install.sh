#!/bin/sh
# =============================================================================
# Universal Multi-Agent Skills Installer (POSIX sh compliant)
# Supports 7+ AI host ecosystems across Project-local and User-Global scopes.
# =============================================================================
set -eu

ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$ROOT/.agents/skills"
USER_HOME="${HOME:-~}"
RUNTIME_DIR="$ROOT/.runtime"
RECEIPT_FILE="$RUNTIME_DIR/installed_receipt.json"
LOCK_FILE="$RUNTIME_DIR/install.lock"

SCOPE="project"
TARGET="auto"
SKILL="all"
FORCE=0
ROLLBACK=0

show_help() {
  cat << EOF
Usage: $0 [OPTIONS]

Options:
  --scope <project|global>   Install scope (default: project)
  --target <auto|all|hosts>  Target hosts (default: auto; e.g. claude,codex,antigravity)
  -s, --skill <all|skills>   Install specific skill(s) (comma-separated; default: all)
  --force                    Apply changes (default: dry-run)
  --rollback                 Rollback previous installation via receipt
  -h, --help                 Show this help message

EOF
  exit 0
}

while [ $# -gt 0 ]; do
  case "$1" in
    --scope) SCOPE="$2"; shift 2 ;;
    --target) TARGET="$2"; shift 2 ;;
    -s|--skill) SKILL="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    --rollback) ROLLBACK=1; shift ;;
    -h|--help) show_help ;;
    *) echo "Unknown option: $1"; show_help ;;
  esac
done

if [ "$ROLLBACK" -eq 1 ]; then
  echo "=== Rolling back skills installation (POSIX) ==="
  if [ ! -f "$RECEIPT_FILE" ]; then
    echo "Error: No receipt file found at '$RECEIPT_FILE' to rollback." >&2
    exit 1
  fi

  # Restore backups
  grep -o '"dest": "[^"]*", "backup": "[^"]*"' "$RECEIPT_FILE" 2>/dev/null | while IFS= read -r line; do
    dest="$(echo "$line" | sed -e 's/.*"dest": "\([^"]*\)".*/\1/')"
    bak="$(echo "$line" | sed -e 's/.*"backup": "\([^"]*\)".*/\1/')"
    if [ -f "$bak" ]; then
      cp -f "$bak" "$dest"
      rm -f "$bak"
      echo "  [RESTORED] $dest from backup"
    fi
  done

  # Remove newly installed files that had no backup
  sed -n '/"new_files": \[/,/\]/p' "$RECEIPT_FILE" | grep '^[[:space:]]*"' | sed -e 's/^[[:space:]]*"//' -e 's/",\?$//' | while IFS= read -r nf; do
    if [ -f "$nf" ]; then
      rm -f "$nf"
      echo "  [REMOVED] $nf"
    fi
  done

  rm -f "$RECEIPT_FILE"
  echo "ROLLBACK COMPLETE"
  exit 0
fi

if [ ! -d "$SRC" ]; then
  echo "Error: Canonical skills directory not found at '$SRC'" >&2
  exit 1
fi

mkdir -p "$RUNTIME_DIR"

# Concurrency lock with wait-retry loop
lock_wait=0
while [ -f "$LOCK_FILE" ]; do
  if [ "$lock_wait" -ge 10 ]; then
    echo "Warning: Overriding stale installer lock..."
    break
  fi
  echo "Waiting for active installer lock..."
  sleep 1
  lock_wait=$((lock_wait + 1))
done
echo "$$" > "$LOCK_FILE"

TRACK_DIR="$RUNTIME_DIR/tmp_track_$$"
if [ "$FORCE" -eq 1 ]; then
  mkdir -p "$TRACK_DIR"
fi

cleanup() {
  rm -f "$LOCK_FILE"
  rm -rf "$TRACK_DIR"
}
trap cleanup EXIT INT TERM

# Hash helper
calc_hash() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | cut -d' ' -f1
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | cut -d' ' -f1
  else
    cksum "$1" | cut -d' ' -f1
  fi
}

echo "=== Universal Multi-Agent Skills Installer (POSIX) ==="
echo "Scope:  $SCOPE"
echo "Target: $TARGET"
echo "Skill:  $SKILL"
echo "Action: $([ "$FORCE" -eq 1 ] && echo "APPLYING CHANGES" || echo "DRY-RUN (use --force to apply)")"
echo ""

if [ "$SKILL" != "all" ]; then
  old_ifs="$IFS"
  IFS=','
  for req in $SKILL; do
    req_trimmed="$(echo "$req" | tr -d '[:space:]')"
    [ -z "$req_trimmed" ] && continue
    if [ ! -d "$SRC/$req_trimmed" ]; then
      echo "Error: Skill '$req_trimmed' not found in canonical skills directory '$SRC'" >&2
      exit 1
    fi
  done
  IFS="$old_ifs"
fi

process_target() {
  hid="$1"
  hname="$2"
  rproj="$3"
  rglob="$4"

  if [ "$SCOPE" = "global" ]; then
    tbase="$USER_HOME/$rglob"
  else
    tbase="$ROOT/$rproj"
  fi

  if [ "$TARGET" != "all" ] && [ "$TARGET" != "auto" ]; then
    case ",$TARGET," in
      *,"$hid",*) ;;
      *) return 0 ;;
    esac
  elif [ "$TARGET" = "auto" ]; then
    if [ "$SCOPE" = "global" ]; then
      if [ "$hid" != "agents" ] && [ ! -d "$USER_HOME/$(dirname "$rglob")" ] && [ ! -d "$USER_HOME/$rglob" ]; then
        return 0
      fi
    else
      if [ "$hid" != "agents" ] && [ ! -d "$ROOT/$rproj" ]; then
        case "$hid" in
          claude|opencode|antigravity) ;;
          *) return 0 ;;
        esac
      fi
    fi
  fi

  echo "--> Target: $hname [$hid]"
  echo "    Directory: $tbase"

  for d in "$SRC"/*/; do
    [ -d "$d" ] || continue
    sname="$(basename "$d")"
    if [ "$SKILL" != "all" ]; then
      case ",$SKILL," in
        *,"$sname",*) ;;
        *) continue ;;
      esac
    fi
    dest_skill="$tbase/$sname"

    # Exclude __pycache__ and *.pyc
    find "$d" -type f ! -path '*/__pycache__/*' ! -name '*.pyc' | while IFS= read -r f; do
      rel="${f#$d}"
      dp="$dest_skill/$rel"

      if [ "$FORCE" -eq 0 ]; then
        echo "  [WOULD-COPY] \"$(basename "$f")\" -> \"$dp\""
        continue
      fi

      if [ -f "$dp" ]; then
        ha="$(calc_hash "$f")"
        hb="$(calc_hash "$dp")"
        if [ "$ha" = "$hb" ]; then
          continue
        fi
        bak_file="$dp.bak-$(date +%Y%m%d-%H%M%S)"
        cp -f "$dp" "$bak_file"
        echo "$dp|$bak_file" >> "$TRACK_DIR/backups.txt"
      else
        echo "$dp" >> "$TRACK_DIR/new_files.txt"
      fi

      mkdir -p "$(dirname "$dp")"
      staging_file="$dp.tmp.$$"
      cp -f "$f" "$staging_file"
      mv -f "$staging_file" "$dp"
      echo "$dp" >> "$TRACK_DIR/installed.txt"
      echo "  [INSTALLED] \"$(basename "$f")\" -> \"$dp\""
    done
  done
}

process_target "agents"      "Open Agents Standard"  ".agents/skills"           ".agents/skills"
process_target "antigravity" "Antigravity / Gemini"  ".gemini/skills"           ".gemini/skills"
process_target "claude"      "Claude Code / CLI"     ".claude/skills"           ".claude/skills"
process_target "codex"       "OpenAI Codex"          ".codex/skills"            ".codex/skills"
process_target "opencode"    "OpenCode"              ".opencode/skills"         ".config/opencode/skills"
process_target "cursor"      "Cursor"                ".cursor/skills"           ".cursor/skills"
process_target "windsurf"    "Codeium Windsurf"      ".windsurf/skills"         ".codeium/windsurf/skills"
process_target "copilot"     "GitHub Copilot"        ".copilot/skills"          ".copilot/skills"

# Write transaction receipt in pure POSIX format
if [ "$FORCE" -eq 1 ]; then
  cat << EOF > "$RECEIPT_FILE"
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date +%Y-%m-%dT%H:%M:%SZ)",
  "scope": "$SCOPE",
  "target": "$TARGET",
  "skill": "$SKILL",
  "installed": [
$(if [ -f "$TRACK_DIR/installed.txt" ]; then
    sed 's/\\/\\\\/g; s/"/\\"/g; s/^/    "/; s/$/",/' "$TRACK_DIR/installed.txt" | sed '$ s/,$//'
  fi)
  ],
  "backups": [
$(if [ -f "$TRACK_DIR/backups.txt" ]; then
    awk -F'|' '{ printf "    {\"dest\": \"%s\", \"backup\": \"%s\"},\n", $1, $2 }' "$TRACK_DIR/backups.txt" | sed '$ s/,$//'
  fi)
  ],
  "new_files": [
$(if [ -f "$TRACK_DIR/new_files.txt" ]; then
    sed 's/\\/\\\\/g; s/"/\\"/g; s/^/    "/; s/$/",/' "$TRACK_DIR/new_files.txt" | sed '$ s/,$//'
  fi)
  ]
}
EOF
fi

echo ""
echo "Done. (DryRun=$([ "$FORCE" -eq 1 ] && echo "false" || echo "true"))"
