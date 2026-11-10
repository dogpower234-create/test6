#!/bin/bash
# Commit the named files and push the current branch to origin.
# Refuses to run if the branch is behind origin.
#
# Usage: bin/cpush.sh [-C] -m MESSAGE FILE...
#   -m MESSAGE  commit message (use $'line1\n\nbody' for a body)
#   -C          append a Claude Co-Authored-By trailer
set -euo pipefail

cd "$(dirname "$0")/.."
MSG=""
CLAUDE=0
while getopts "Cm:" opt; do
    case $opt in
        C) CLAUDE=1 ;;
        m) MSG=$OPTARG ;;
        *) sed -n '2,/^set /p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; exit 2 ;;
    esac
done
shift $((OPTIND - 1))

if [ -z "$MSG" ] || [ $# -eq 0 ]; then
    echo "Usage: bin/cpush.sh [-C] -m MESSAGE FILE..." >&2
    exit 2
fi
if [ $CLAUDE -eq 1 ]; then
    MSG="$MSG"$'\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)
git fetch -q origin
if [ "$(git rev-list --count "HEAD..origin/$BRANCH")" -ne 0 ]; then
    echo "$BRANCH is behind origin/$BRANCH; pull first." >&2
    exit 1
fi

git add -- "$@"
git commit -q -m "$MSG"
git push origin "$BRANCH"
git log --oneline -1
git status -sb
