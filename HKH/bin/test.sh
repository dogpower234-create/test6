#!/bin/bash
# Run the project's tests with the venv active and PYTHONPATH set.
#
# Usage:
#   bin/test.sh              # full suite: lint + tests (make all_tests)
#   bin/test.sh PATH...      # quick: pytest -q on the given paths
#
# Example: bin/test.sh states server/tests/test_endpoints.py
set -euo pipefail

cd "$(dirname "$0")/.."
set +u
source geodata2026-venv/bin/activate
set -u
export PYTHONPATH=$PWD
export GEODATA_DB=test_geodata2026  # never test against real data

if [ $# -eq 0 ]; then
    make all_tests
else
    python -m pytest -q -p no:cacheprovider --import-mode=importlib "$@"
fi
