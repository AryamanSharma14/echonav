#!/usr/bin/env bash
# Helper: append a PROGRESS.md entry, commit, then push.
# Usage: ./scripts/log-push.sh "Done: X. Next: Y. Notes: Z."
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 \"Done: ... Next: ... Notes: ...\""
  exit 1
fi

NAME=$(git config user.name)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
STAMP=$(date +"%Y-%m-%d %H:%M")
MSG="$1"

# Insert new entry below the marker in docs/PROGRESS.md
TMP=$(mktemp)
awk -v entry="## $STAMP — $NAME — $BRANCH\n- $MSG\n" '
  /<!-- New entries go here -->/ { print; print ""; print entry; next }
  { print }
' docs/PROGRESS.md > "$TMP" && mv "$TMP" docs/PROGRESS.md

git add docs/PROGRESS.md docs/TODO.md
git commit -m "log: $BRANCH — $(echo "$MSG" | head -c 60)" || true
git push
echo "Logged and pushed."
