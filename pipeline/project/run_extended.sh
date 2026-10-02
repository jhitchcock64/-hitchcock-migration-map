#!/usr/bin/env bash
# Builds everything the site ships, in two passes of the pipeline (about a minute):
#
#   1. the extended run (HM_EXT=1): the core map plus every cousin and the cousins' other lines
#      (extset.py) -> data_ext.js, profiles_ext.js. A page loads these instead of data.js only when
#      the "Viewing as" person is outside the core (viewer.js), so ordinary visitors never download them.
#   2. the core run -> data.js, profiles.js, private_photos.js, relatives.js, exactly as
#      run_pipeline.sh + write_data_js.py always did. It runs last, so the pipeline's output on disk
#      (and diff_shipped.py, check_page.py) is the core's.
#
#   GEDCOM="/path/to/export.ged" HM_PASSPHRASE=... bash pipeline/project/run_extended.sh
#
# Run diff_shipped.py against the live data.js BEFORE this if the tree changed (RUNBOOK.md): this script
# overwrites data.js.
set -euo pipefail
: "${GEDCOM:?Set GEDCOM=/path/to/export.ged}"
: "${HM_PASSPHRASE:?Set HM_PASSPHRASE (the family password; see privacy.py)}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
PY=""
for c in python3 python "py -3"; do
  if $c -c 'import sys; sys.exit(sys.version_info[0] != 3)' >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "No working Python 3 found"; exit 1; }
export PYTHONUTF8=1

echo "== extended run"
HM_EXT=1 bash "$HERE/run_pipeline.sh"
( cd "$ROOT" && $PY pipeline/project/write_data_js.py data_ext.js | grep -v "unchanged" )

echo "== core run"
bash "$HERE/run_pipeline.sh"
( cd "$ROOT" && $PY pipeline/project/write_data_js.py data.js | grep -v "unchanged" )
