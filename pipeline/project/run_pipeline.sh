#!/bin/bash
# Rebuild all map data from a GEDCOM export.
#   Usage:  GEDCOM=/path/to/export.ged bash pipeline/project/run_pipeline.sh
# Works from any directory. Outputs land in pipeline/build2/*.json; logs in pipeline/logs/.
set -euo pipefail
export PYTHONHASHSEED=0   # makes tie-breaks between equivalent place labels reproducible
: "${GEDCOM:?Set GEDCOM=/path/to/export.ged}"
export GEDCOM="$(cd "$(dirname "$GEDCOM")" && pwd)/$(basename "$GEDCOM")"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$HERE/../logs"; mkdir -p "$LOG"
trap 'echo "PIPELINE FAILED -- last log lines:"; tail -25 "$(ls -t "$LOG"/*.log | head -1)"' ERR
run() { echo "  $1"; python3 "$1" > "$LOG/${1%.py}.log" 2>&1; }
echo "Stage 1-4 (pipeline/project):"; cd "$HERE"
run 01_extract_ancestors.py; run 02_extract_events.py; run 03_build_legs.py; run 04_build_routes.py
echo "Stage 5-7 (pipeline/build2):"; cd "$HERE/../build2"
run build_anchors.py; run build_family_tags.py; run rebuild_all_data.py
grep -m1 "James+Jennie family record" "$LOG/01_extract_ancestors.log" || true
tail -6 "$LOG/rebuild_all_data.log"
