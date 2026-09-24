# Hitchcock migration map — pipeline runbook

This folder is the actual source for index.html's data arrays (ROUTES, PLACES,
GRAPH, SEARCH_INDEX, PERSON_LEGS, CLUSTERS). index.html is generated output --
always update it by rerunning this pipeline, never by hand-editing the arrays
or splicing in data from a separate one-off script. That drift is what broke
the map on 2026-09-23; see "History" below.

Verified 2026-09-24 against commit 78f1cc4: 586/590 people with byte-identical
migration legs, and graph/search-index/places/clusters counts all matching.

## Layout
- pipeline/project/  01_extract_ancestors.py, 02_extract_events.py, geocoder.py,
                      03_build_legs.py, 04_build_routes.py, graft.py,
                      diff_shipped.py, run_pipeline.sh
- pipeline/build2/    build_anchors.py, build_family_tags.py, rebuild_all_data.py

Scripts read/write relative to their own directory unless noted. Copy
pipeline/project and pipeline/build2 to /home/claude/ before running (or edit
the paths at the top of each script) -- they expect those absolute locations.

## Updating for a new GEDCOM export
1. `cp pipeline/project/*.py /home/claude/project/ && cp pipeline/build2/*.py /home/claude/build2/`
   (create those two directories first if they don't exist)
2. Unzip the new export; copy it to /home/claude/project/, then set
   GEDCOM_PATH in 01_extract_ancestors.py and 02_extract_events.py.
3. Family IDs shift on every export; individual IDs (@I...@) do not.
   Look up James+Jennie's marriage FAM -- the FAM whose HUSB is
   @I240014574891@ and WIFE is @I242606531603@ -- and set
   JAMES_JENNIE_FAM_ID in 01_extract_ancestors.py to it.
4. `bash /home/claude/project/run_pipeline.sh`
5. Diff against the currently-live page before touching anything else:
   `curl -s https://raw.githubusercontent.com/jhitchcock64/-hitchcock-migration-map/main/index.html -o /tmp/live.html && python3 diff_shipped.py /tmp/live.html`
   Every person who was already correct on the live map should still match
   exactly. Investigate before proceeding if that count drops.
6. For newly-added ancestors specifically, list unresolvable place strings
   (`geocoder.normalize_and_geocode(raw) is None`) and add geocoder entries
   as needed, then rerun steps 4-5.
7. Graft the verified output into the live page -- never string-splice or
   append, since GRAPH/SEARCH_INDEX are keyed dicts/arrays where a duplicate
   ID silently loses to whichever copy appears later in the file:
   `python3 pipeline/project/graft.py <path to current index.html> index.html`
8. Sanity-check in a browser before pushing: search for a few people you
   know are new, confirm they show a location and (if they have 2+ located
   events) a journey line, and confirms parents resolve correctly for at
   least one multi-generation chain.
9. Commit and push to main.

## Projection
x = lon + 35 (wrapped to [-180, 180)), y = 65 - lat. A plain equirectangular
shift, not a true map projection -- reverse-engineered 2026-09-23 by solving
REF_CITIES' known real-world coordinates against their plotted x/y.

## Notes
- geocoder.py's RAW_GROUND_TRUTH table (checked before all other rules) pins
  exact raw GEDCOM place strings to the location the live map has always used
  for them, so re-running the pipeline can't silently redraw an already-
  correct person's route. A value of None means that string was deliberately
  left unresolved on the live map (add a real entry only if you're fixing it
  on purpose). Extend this table the same way it was built: align a person's
  stops against the live map's PERSON_LEGS for that person, not by guessing.
- 02_extract_events.py carries hand-authored corrections (John Grove Speer's
  1850/1857 gold-rush journey from his own memoir, and fixes for specific
  individuals -- search the file for "ad hoc" and "correction"). Keep these;
  they encode real research, not pipeline bugs.
- PYTHONHASHSEED=0 is pinned in run_pipeline.sh so that ties between
  equivalent place labels resolve the same way on every run.

## History
2026-08 through 2026-09-21: pipeline developed and refined across ~15
sessions, but only ever run from ephemeral session state -- never committed.
2026-09-23: a from-scratch rebuild (without consulting this pipeline) shipped
a broken update -- ancestors searchable with no location data, because it
never built GRAPH/SEARCH_INDEX at all, and a first attempt to fix that
string-spliced new entries in rather than merging, which silently lost to
stale duplicate keys. The pipeline was recovered by replaying every relevant
edit across all prior session transcripts in order, verified by diffing its
output against the then-live map, and committed here specifically so this
can't happen again -- if you're reading this because something looks wrong,
start with step 5 above before rebuilding anything from scratch.
