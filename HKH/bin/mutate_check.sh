#!/bin/bash
# Check that the tests catch the removal of a line of code (e.g. a
# security check): replace the line with `pass`, run the tests, restore
# the file. Exits 0 if some test failed (good: the removal was caught),
# 1 if every test still passed.
#
# Usage: bin/mutate_check.sh FILE 'EXACT LINE TEXT' [TEST_PATH...]
#   The line text is matched after stripping indentation, and must
#   occur exactly once in FILE. Test paths default to: data common states counties server
#
# Example:
#   bin/mutate_check.sh server/endpoints.py \
#       'check_permission(sec.STATES, sec.DELETE)' server
set -euo pipefail

if [ $# -lt 2 ]; then
    sed -n '2,/^set /p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'
    exit 2
fi

cd "$(dirname "$0")/.."
FILE=$1
LINE=$2
shift 2
[ $# -eq 0 ] && set -- data common states counties server

BACKUP=$(mktemp)
cp "$FILE" "$BACKUP"
trap 'cp "$BACKUP" "$FILE"; rm -f "$BACKUP"' EXIT

python3 - "$FILE" "$LINE" <<'PY'
import sys
path, target = sys.argv[1], sys.argv[2].strip()
lines = open(path).read().split('\n')
hits = [i for i, ln in enumerate(lines) if ln.strip() == target]
if len(hits) != 1:
    sys.exit(f"Expected exactly 1 line matching {target!r} in {path}, "
             f"found {len(hits)}.")
i = hits[0]
indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
lines[i] = indent + 'pass'
open(path, 'w').write('\n'.join(lines))
PY

echo "=== Removed from $FILE: $LINE ==="
if bin/test.sh "$@"; then
    echo "MUTATION SURVIVED: all tests passed without that line." >&2
    exit 1
fi
echo "OK: tests caught the removal."
