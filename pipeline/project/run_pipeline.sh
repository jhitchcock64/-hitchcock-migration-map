#!/bin/bash
# Rebuild all map data from a GEDCOM export.
#   Usage:  GEDCOM=/path/to/export.ged bash pipeline/project/run_pipeline.sh
# Works from any directory. Outputs land in pipeline/build2/*.json; logs in pipeline/logs/.
set -euo pipefail
export PYTHONHASHSEED=0   # makes tie-breaks between equivalent place labels reproducible
export PYTHONUTF8=1       # read/write files as UTF-8 everywhere (Windows otherwise defaults to cp1252)
: "${GEDCOM:?Set GEDCOM=/path/to/export.ged}"
export GEDCOM="$(cd "$(dirname "$GEDCOM")" && pwd)/$(basename "$GEDCOM")"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$HERE/../logs"; mkdir -p "$LOG"
trap 'echo "PIPELINE FAILED -- last log lines:"; tail -25 "$(ls -t "$LOG"/*.log | head -1)"' ERR
# A working Python 3: on Windows `python3` is often only the Microsoft Store
# placeholder, and `python` or `py -3` is the real one.
PY=""
for c in python3 python "py -3"; do
  if $c -c 'import sys; sys.exit(sys.version_info[0] != 3)' >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "No working Python 3 found (tried python3, python, py -3)"; exit 1; }
run() { echo "  $1"; $PY "$1" > "$LOG/${1%.py}.log" 2>&1; }
echo "Stage 1-4 (pipeline/project):"; cd "$HERE"
run 01_extract_ancestors.py; run 02_extract_events.py; run 03_build_legs.py; run 04_build_routes.py
echo "Stage 5-7 (pipeline/build2):"; cd "$HERE/../build2"
run build_anchors.py; run build_family_tags.py; run rebuild_all_data.py
grep -m1 "James+Jennie family record" "$LOG/01_extract_ancestors.log" || true
tail -6 "$LOG/rebuild_all_data.log"
