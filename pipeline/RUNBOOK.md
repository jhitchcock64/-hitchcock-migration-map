# Pipeline runbook: updating the map from a new GEDCOM export

The six data arrays in `data.js` (ROUTES, CLUSTERS, PLACES, SEARCH_INDEX,
GRAPH, PERSON_LEGS) are generated output. Always update them by running this
pipeline and writing the result with `write_data_js.py`. Never hand-edit or
splice them. (`data.js` also carries VB, which the pipeline doesn't
produce; `write_data_js.py` keeps it byte for byte.)

Needs only Python 3 (standard library). Runs from any directory on any machine.
On Windows, run the `.sh` step in Git Bash and the Python steps with `python`
(on James's laptop `python3` is only the Microsoft Store placeholder; the
runner finds a working Python by itself and sets UTF-8 mode).

## Steps

1. **Get the export.** James exports the tree from Ancestry as a GEDCOM (a .ged
   file, usually inside a zip; his land in `Downloads` as
   `Albert Hitchcock Family Tree (N).zip`). Unzip it OUTSIDE the repo. It
   contains living people and must never be committed.

2. **Run the pipeline** (in Git Bash on Windows):

   ```
   GEDCOM="/path/to/Albert Hitchcock Family Tree.ged" bash pipeline/project/run_pipeline.sh
   ```

   It prints each stage, the James+Jennie family record it detected, and a
   summary (routes, places, people). Logs go to `pipeline/logs/`. Outputs go to
   `pipeline/build2/*.json`.

   The James+Jennie family ID changes on every export; the pipeline finds it
   automatically. If detection ever fails, set `JAMES_JENNIE_FAM_ID=@F####@`.

3. **List unresolved places**, focusing on people who are new in this export,
   and add geocoder entries where they matter:

   ```
   cd pipeline/project && python -c "
   import json, geocoder
   ev = json.load(open('events.json'))
   bad = sorted({e['plac'] for r in ev.values() for e in r['events']
                 if e.get('plac') and e['type'] in ('BIRT','RESI','DEAT')
                 and geocoder.normalize_and_geocode(e['plac']) is None})
   print(len(bad)); print('\n'.join(bad))"
   ```

   Also check that new places resolved to the RIGHT spot, not a state-level
   fallback. (Example: Middlesex County, VA strings once fell back to the
   "Virginia" centroid, about 110 miles off.) Rerun step 2 after any edit.

4. **Diff against the live data** before touching `data.js`:

   ```
   python pipeline/project/diff_shipped.py data.js
   ```

   Every person who matched before should still match. Investigate any drop.
   New people appearing is expected. Explain every difference (new people,
   changed legs, changed routes) from the tree's own edits before shipping;
   comparing the person's GEDCOM record in the old and new export usually
   shows it.

5. **Write** the new arrays into `data.js`:

   ```
   python pipeline/project/write_data_js.py data.js
   ```

6. **Check the page in a browser:**

   ```
   python tools/check_page.py index.html --shot map.png
   ```

   Then open it yourself (serve the repo: `python -m http.server 8000`, then
   http://localhost:8000/) and look at a few people you know changed.

7. **Commit and push** to `main`, with James's OK. GitHub Pages rebuilds in
   about a minute.

`legacy.html` (the pre-rebuild page, data inline) is frozen and isn't
updated by these steps.

## How the geocoder decides (pipeline/project/geocoder.py)

Checked in this order for each raw GEDCOM place string:

- `RAW_GROUND_TRUTH`: exact raw string → `(label, lat, lon, tier)`, or `None`
  meaning "deliberately unresolved". Pins placements the approved map already
  used, so reruns can't silently move anyone. Extend it only from evidence
  (the live map's own data), never by guessing.
- `SPECIAL_CASES`: exact lowercase raw string → `(label, lat, lon, tier)`.
- Parsed `town|state` and `county|state` tables. Counties resolve to their
  county seat and get labels like "Middlesex Co., Virginia".
- State and country fallbacks (tiers `region` / `country`).

Downstream, `03_build_legs.py` merges stops within a short distance, collapses
brief side trips, and drops state-level "generic" stops when the same person
has a specific stop in that state.

## Hand corrections

`02_extract_events.py` carries corrections James asked for, including John
Grove Speer's 1850/1857 gold-rush journey (23 waypoints from his memoir) and
event removals for specific individuals. Search the file for "ad hoc" and
"correction". Keep them; they encode research. Some filter blocks appear more
than once (a leftover from the recovery). They're idempotent, so they're
harmless.

## Projection

`x = longitude + 35` (wrapped to [-180, 180)), `y = 65 - latitude`. A plain
equirectangular map centered on the Atlantic.

## Reproducibility

`run_pipeline.sh` pins `PYTHONHASHSEED=0`. Without it, ties between equivalent
labels for the same place (e.g. "Daviess Co., Kentucky" vs "Owensboro,
Kentucky") can flip between runs.

## History

Built across ~15 claude.ai sessions in Aug–Sep 2026, running only in temporary
sandboxes and never committed. On 2026-09-23 a rebuild done without it broke
the live map. The pipeline was recovered by replaying every recorded edit from
the session transcripts, then verified against the live map: 586/590 people
had identical legs and all 1,265 birthplaces matched. It was committed so this
can't recur. On 2026-09-24 it was made portable (no hardcoded sandbox paths)
and verified byte-identical on all six arrays, then made to run on Windows
and verified again there (the 2026-09-23 export reproduces the live data
byte for byte). The same day the data moved out of `index.html` into
`data.js`, and `write_data_js.py` replaced `graft.py`.

## The basemap

`basemap/county_lines.js` and `basemap/fallback.js` don't depend on the
GEDCOM and rarely need rebuilding: `python pipeline/basemap/build_basemap.py`
(see its docstring for the public-domain inputs in `pipeline/basemap/cache/`).
The rest of the background map comes from OpenFreeMap at run time.
