#!/bin/bash
# Replace the USStates collection in the local MongoDB with the states
# in a CSV file, renamed to our field names (see states/load.py).
#
# Usage: bin/load_states.sh [CSV]     (default: states/raw_data/states.csv)
set -euo pipefail

cd "$(dirname "$0")/.."
set +u
source geodata2026-venv/bin/activate
set -u
export PYTHONPATH=$PWD

python states/load.py "${1:-states/raw_data/states.csv}"
