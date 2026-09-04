#!/usr/bin/env bash
# sync-installed.sh — keep the installed copy under $HOME/.claude in step with this repository.
#
# A manual install leaves a second copy of every file on disk. Editing the repository and
# forgetting the copy (or overwriting a newer copy with an older one) has cost real work,
# so this does the comparison and the copying, and never overwrites without a backup.
#
# Usage:
#   scripts/sync-installed.sh --check     # list what differs; change nothing
#   scripts/sync-installed.sh --apply     # back up, then copy repository -> installed
#   scripts/sync-installed.sh --help
#
# What is synced (repository -> $HOME/.claude):
#   skills/ctx-*/SKILL.md   ->  $HOME/.claude/skills/<skill>/SKILL.md
#   agents/digest.md        ->  $HOME/.claude/agents/digest.md
#   scripts/cache-audit.py  ->  $HOME/.claude/scripts/cache-audit.py
#
# What is only reported, never written:
#   hooks/hooks.json vs the `hooks` section of $HOME/.claude/settings.json — that file is
#   yours and holds settings of your own, so merge the section by hand (README, manual
#   install). The hook line never affects the exit code.
#
# --apply copies only what differs, and every file it is about to overwrite is copied first
# into $HOME/.claude/ctx-kit-backup-<timestamp>/ (same relative path), with a MANIFEST.txt
# listing every action. Nothing is ever deleted.
#
# $HOME decides where "installed" is: run it with `HOME=/tmp/somewhere` to rehearse safely.
#
# Exit codes:
#   0  in sync (or --apply finished and everything now matches)
#   1  --check found differences (file drift only; the hooks line does not count)
#   2  usage error, or the repository/HOME could not be resolved
set -u

ROOT=$(cd "$(dirname "$0")/.." && pwd)
MODE=""
for a in "$@"; do
  case "$a" in
    --check) MODE=check ;;
    --apply) MODE=apply ;;
    -h|--help)
      sed -n '2,/^set -u/p' "$0" | sed 's/^# \{0,1\}//; $d'
      exit 0 ;;
    *) echo "unknown argument: $a" >&2
       echo "usage: sync-installed.sh [--check|--apply|--help]" >&2
       exit 2 ;;
  esac
done
if [ -z "$MODE" ]; then
  echo "usage: sync-installed.sh [--check|--apply|--help]" >&2
  exit 2
fi
if [ -z "${HOME:-}" ] || [ ! -d "${HOME:-/nonexistent}" ]; then
  echo "cannot run: HOME is not set to a directory" >&2
  exit 2
fi
DEST="$HOME/.claude"

pick_python() {
  # the macOS /usr/bin/python3 shim fails on `import json` with an xcodebuild error;
  # probing rather than guessing keeps us off it
  for c in ${CTXKIT_PYTHON:-} python3 /usr/local/bin/python3 /opt/homebrew/bin/python3; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import json' >/dev/null 2>&1; then
      echo "$c"; return 0
    fi
  done
  return 1
}

pairs() {
  for f in "$ROOT"/skills/ctx-*/SKILL.md; do
    [ -f "$f" ] || continue
    printf '%s\tskills/%s/SKILL.md\n' "$f" "$(basename "$(dirname "$f")")"
  done
  [ -f "$ROOT/agents/digest.md" ] && printf '%s\tagents/digest.md\n' "$ROOT/agents/digest.md"
  [ -f "$ROOT/scripts/cache-audit.py" ] && printf '%s\tscripts/cache-audit.py\n' "$ROOT/scripts/cache-audit.py"
  return 0
}

echo "# repository: $ROOT"
echo "# installed:  $DEST"

DIFFS=0
COPIED=0
BK=""
while IFS="$(printf '\t')" read -r src rel; do
  [ -n "${src:-}" ] || continue
  dst="$DEST/$rel"
  if [ ! -f "$dst" ]; then
    state="not installed"
  elif cmp -s "$src" "$dst"; then
    state="same"
  else
    state="differs"
  fi
  if [ "$state" = "same" ]; then
    [ "$MODE" = check ] && printf "  %-14s%s\n" "same" "$rel"
    continue
  fi
  DIFFS=$((DIFFS + 1))
  if [ "$MODE" = check ]; then
    printf "  %-14s%s\n" "$state" "$rel"
    continue
  fi
  if [ -z "$BK" ]; then
    BK="$DEST/ctx-kit-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BK" || exit 2
    { echo "ctx-kit sync-installed.sh backup"; echo "date: $(date)"; echo "repository: $ROOT"; } > "$BK/MANIFEST.txt"
  fi
  if [ -f "$dst" ]; then
    mkdir -p "$(dirname "$BK/$rel")"
    cp -p "$dst" "$BK/$rel" || exit 2
    echo "replaced (backed up): $rel" >> "$BK/MANIFEST.txt"
    printf "  %-14s%s\n" "backed up +" "$rel"
  else
    echo "added (was not installed): $rel" >> "$BK/MANIFEST.txt"
    printf "  %-14s%s\n" "copied (new)" "$rel"
  fi
  mkdir -p "$(dirname "$dst")"
  cp -p "$src" "$dst" || exit 2
  COPIED=$((COPIED + 1))
done <<EOF
$(pairs)
EOF

# hooks: report only
HOOKS_SRC="$ROOT/hooks/hooks.json"
SETTINGS="$DEST/settings.json"
if [ ! -f "$HOOKS_SRC" ]; then
  echo "  hooks         hooks/hooks.json is missing from the repository"
elif [ ! -f "$SETTINGS" ]; then
  echo "  hooks         no $SETTINGS — the PreCompact hook is not installed; merge the \`hooks\` object from hooks/hooks.json by hand"
else
  PY=$(pick_python) || PY=""
  if [ -z "$PY" ]; then
    echo "  hooks         no usable python3 found — hook comparison skipped"
  else
    "$PY" - "$HOOKS_SRC" "$SETTINGS" <<'PYEOF'
import json, sys
def load(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print(f"  hooks         {p} does not parse ({e})")
        raise SystemExit(0)
src = load(sys.argv[1]).get("hooks", {})
cur = load(sys.argv[2]).get("hooks", {})
missing = [k for k in src if k not in cur]
diff = [k for k in src if k in cur and json.dumps(cur[k], sort_keys=True, ensure_ascii=False)
        != json.dumps(src[k], sort_keys=True, ensure_ascii=False)]
if missing:
    print(f"  hooks         settings.json has no {', '.join(missing)} hook — merge it by hand (never merged automatically)")
if diff:
    print(f"  hooks         settings.json {', '.join(diff)} differs from hooks/hooks.json — merge by hand (never merged automatically)")
if not missing and not diff:
    print(f"  hooks         same ({', '.join(src) or 'nothing to compare'})")
PYEOF
  fi
fi

if [ "$MODE" = check ]; then
  if [ "$DIFFS" -eq 0 ]; then
    echo "--- in sync (files only; the hooks line above is advisory) ---"
    exit 0
  fi
  echo "--- $DIFFS file(s) out of sync — run: $0 --apply ---"
  exit 1
fi

if [ "$COPIED" -eq 0 ]; then
  echo "--- already in sync; nothing copied, no backup made ---"
else
  echo "--- copied $COPIED file(s); backup: $BK ---"
  echo "    note: a running session keeps the skill text it loaded at start — open a new session to use the changes"
fi
exit 0
