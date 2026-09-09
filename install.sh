#!/bin/sh
# ponytail: minimal copy, sha256 compare only; add rsync when skill count grows
set -eu
ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$ROOT/.agents/skills"
FORCE=0
for a in "$@"; do [ "$a" = "--force" ] && FORCE=1; done
if [ "$FORCE" -eq 0 ]; then echo "DRY-RUN: rerun with --force to apply."; fi
for d in "$SRC"/*/; do
  [ -d "$d" ] || continue
  name="$(basename "$d")"
  for t in ".claude/skills" ".opencode/skills" ".gemini/skills"; do
    dest="$ROOT/$t/$name"
    find "$d" -type f | while IFS= read -r f; do
      rel="${f#$d}"
      dp="$dest/$rel"
      if [ "$FORCE" -eq 0 ]; then echo "WOULD-COPY: \"$f\" -> \"$dp\""; continue; fi
      if [ -f "$dp" ]; then
        a="$(sha256sum "$f" | cut -d' ' -f1)"; b="$(sha256sum "$dp" | cut -d' ' -f1)"
        if [ "$a" = "$b" ]; then continue; fi
        cp "$dp" "$dp.bak-$(date +%Y%m%d-%H%M%S)"
      fi
      mkdir -p "$(dirname "$dp")"
      cp "$f" "$dp"
      echo "COPIED: \"$f\" -> \"$dp\""
    done
  done
done
echo "DONE (force=$FORCE)"
