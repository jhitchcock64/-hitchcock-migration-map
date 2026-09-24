# Hitchcock migration map

Interactive map of every documented migration among the direct ancestors of
Margaret Jean Hitchcock. Margaret is a synthetic root person (b. 2026,
Alexandria VA), the daughter of James Albert Hitchcock (repo owner) and
Jennie Anne Askew. Rooting at her unifies both family trees: 1,280 people
and 897 routes spanning 1545–2026, from England, Ireland, Scotland, Germany,
Switzerland and Sweden through colonial New England and Virginia to the
South and Midwest.

- Live: https://jhitchcock64.github.io/-hitchcock-migration-map/
- Hosting: GitHub Pages, serving `index.html` from the root of `main`.
  Pushing to `main` deploys, usually within a minute or two.
- Source of truth for the family data: James's Ancestry tree, exported as a
  GEDCOM. The GEDCOM is NOT in the repo and must never be committed (it
  contains living people; `.gitignore` blocks `*.ged` and `*.zip`).

## Working with James

- He's a serious genealogy researcher: primary sources, careful reasoning,
  candid when something is wrong. Match that. Say plainly what you verified
  and what you didn't.
- Keep replies concise. Skip preamble and filler.
- James works on **Windows** (PowerShell), and is not a developer by trade.
  Give exact commands to paste, one step at a time. On Windows, Python may
  be `python` or `py` rather than `python3`; the pipeline's `.sh` runner
  needs Git Bash, which comes with Git for Windows. Install missing tools
  (e.g. `winget install Python.Python.3.12`) only with his OK.
- Verify before claiming something works: run the checks, look at
  screenshots. He has been burned by "done" that wasn't.
- Genealogical facts get corrected in his tree, not in code. The exceptions
  are the documented hand corrections in `pipeline/project/02_extract_events.py`.
- Ask before pushing to `main`, since that deploys the live site. Use his
  normal git credentials. Never write tokens or credentials into any file.

## Repo layout

```
index.html                 the entire site: inline CSS, inline JS, and all data (~1.9 MB)
pipeline/project/          GEDCOM → data stages 1-4, geocoder, graft + diff tools, runner
pipeline/build2/           stages 5-7: anchors, family tags, final arrays
pipeline/RUNBOOK.md        how to update the map from a new GEDCOM (read this for data work)
tools/check_page.py        headless smoke test of the page (key people, errors, counts)
REBUILD_BRIEF.md           the current big task: make the map faster
```

`index.html` loads one external script, d3 7.9.0 from cdnjs. Everything else
is inline.

## Data pipeline (summary; details in pipeline/RUNBOOK.md)

```
GEDCOM="/path/to/export.ged" bash pipeline/project/run_pipeline.sh   # rebuild arrays
python3 pipeline/project/diff_shipped.py index.html                   # compare with live page
python3 pipeline/project/graft.py index.html index.html               # replace arrays in page
python tools/check_page.py index.html                                 # smoke test
```

Pure Python 3 standard library. It runs from any folder, detects the
per-export James+Jennie family ID automatically, and pins `PYTHONHASHSEED=0`
for reproducible output. Verified 2026-09-24: output is byte-identical to the
live data on all six arrays.

Stages:
1. `01_extract_ancestors.py` parses the GEDCOM, injects synthetic Margaret,
   and walks her ancestors → `indi.json`, `fam.json`, `ancestors.json`.
2. `02_extract_events.py` pulls birth/residence/death events and applies
   hand corrections → `events.json`.
3. `geocoder.py` (imported, not run) turns raw place strings into
   `(label, lat, lon, tier)`.
4. `03_build_legs.py` builds each person's stops and legs → `legs.json`.
5. `04_build_routes.py` builds route geometry, including ocean paths →
   `migration_routes.geojson`.
6. `build2/build_anchors.py` and `build_family_tags.py` link routes to people
   and mark families traveling together.
7. `build2/rebuild_all_data.py` produces the six arrays the page uses:
   `routes_prepared.json` → ROUTES, `clusters_prepared.json` → CLUSTERS,
   `places_prepared.json` → PLACES, `search_index.json` → SEARCH_INDEX,
   `person_graph.json` → GRAPH, `person_legs.json` → PERSON_LEGS.

Ocean crossings are computed in the pipeline and shipped as finished
coordinate paths, so any renderer can draw them as-is.

## Coordinates

Everything in the page is in projected units: `x = lon + 35` (wrapped to
[-180,180)), `y = 65 - lat`. This is plain equirectangular, centered on the
Atlantic. Nothing about it is special, and a better projection would be fine
if a rebuild wants one. The SVG viewBox is `VB = {x0:-70, y0:0, w:123, h:58}`.

## Current page architecture (index.html)

Layers, bottom to top:
- `#basemap-svg`: land and state borders as SVG paths from `BASEMAP`. The
  far and near detail versions swap at zoom 3.5 (`land_near` is ~324 KB of
  path data, `land_far` ~165 KB), plus lakes, rivers and Central America.
- `#routes-canvas`: Canvas 2D. All routes, cluster bands and arrowheads,
  redrawn every frame by `drawRoutes()`.
- `#overlay-svg`: place dots (`PLACES`, ~500 circles), reference-city dots,
  pooled place labels, and the convergence ring and label at the target
  person's birthplace.
- `#zoom-capture`: an invisible layer that receives mouse and touch input.
  Zoom is custom (`applyZoomAt`, range 1–60×), not d3-zoom's default.

Rendering loop: input → `scheduleRedraw()` (one requestAnimationFrame) →
`redrawAll()`, which sets the SVG transforms, swaps basemap detail if needed,
resizes every dot, calls `drawRoutes()`, and repositions labels. Label layout
is throttled to about every 100 ms during gestures.

Routes are drawn with:
- Color: `colorForYear(mean_year)`, a rank-based 7-stop palette (see below).
- Width: `lwFor(count)`, by number of ancestors on the route.
- Twin stroke for `family_group` (confirmed family traveling together).
- Dashed for `oscillation` (repeated back-and-forth between nearby towns).
- Arrowheads at the destination.
- Below zoom 4.5 (`AGGREGATE_ZOOM_THRESHOLD`), routes that belong to a
  cluster with at least 2 visible members are hidden and the cluster band is
  drawn instead.

Relevance: `setTarget(person)` computes `TARGET_ANCESTOR_SET`. A route is
drawn if any of its `anchor_ids` is in that set. `recomputeClusterVisibility()`
runs once per target change.

Modes (`#search-modes` buttons, `searchMode`):
- **Family journey** (default): choose a target person; shows the routes of
  that person's ancestors converging on them. The default target is Margaret.
- **Life journey**: one person's own legs from `PERSON_LEGS`.
- **Path between**: the genealogical path between two people (`findPath` /
  `assemblePath`), with status text in `#path-status`.
- **Time period**: from/to year inputs, a play button that steps a window
  2 years every 200 ms from 1545 to 2026 (bounds now derived from the data),
  and an optional person filter (`#era-person-*`).
- **Surname**: filter routes by surname.

Interaction:
- Hover: `handleHover` → hit-test clusters and routes against cached
  screen points (`distToSeg`) → tooltips.
- Click: `handleClick` → a route picker if several overlap, otherwise focus
  the route's generational thread to the target (`focusThread`,
  `renderFocusedChain`), with `#focus-panel` and a dropdown; everything else
  dims.
- Zoom buttons `#zoomIn/#zoomOut/#zoomReset`, level shown in `#zoomLevel`;
  wheel, pinch and drag all work.

Color scale (settled 2026-09-24 after several rounds; don't change without
asking James):
- Stops, oldest → newest: `#0f8a7a #2050d6 #8033d6 #e0359e #f0453f #ff8c1a #e8c020`
  (teal → blue → violet → magenta → red → orange → gold).
- Rank/percentile mapping (`rankT`): a year's color reflects its position
  among all route years, not its place in 1545–2026. About half the routes
  fall in 1750–1870; a linear scale squeezed them into one hue.
- The legend gradient (`#cbGradientCanvas`) is painted from the same
  function, so it can't drift out of sync. The legend labels (1545 / 1841 /
  2026, i.e. min / median / max) and the header's "1545–2026" are still
  hardcoded text and should be derived from the data.
- Rejected, for the record: RdYlBu (its pale-yellow midpoint vanished on
  the tan basemap) and viridis.

Data formats (all coordinates in projected units):
- ROUTES[i]: `id, curve, count, mean_year, min_year, max_year, from, to,
  people[], anchor, anchor_ids[], family_group`, optionally `cluster` and
  `oscillation`. `curve` is either
  `{mode:"bow", x1,y1,cx,cy,x2,y2}` (quadratic arc) or
  `{mode:"path", coords:[[x,y],...]}` (ocean crossings and other waypointed
  routes).
- CLUSTERS[i]: `id, curve, count, mean_year, min_year, max_year, from, to,
  members[]` (indices into ROUTES).
- PLACES[i]: `label, x, y, touches, tier` (1–3; drives label priority).
- SEARCH_INDEX[i]: `id, name, birt, has_moves, has_place`.
- GRAPH: `{james_id (actually Margaret's id), sibling_ids, people:{id:
  {name, surname, by (birth year), bplace, bx, by_y, fx, fy, fplace?, parents[]}}}`.
- PERSON_LEGS: `{id: [{from, to, year, x1,y1,x2,y2, cx,cy, ocean?, waypts?}]}`.
- BASEMAP: SVG path strings, `land_far, land_near, states_far, states_near,
  lakes, rivers, central_america`. Not produced by the pipeline; baked in
  from an earlier session.
- Also static in the page: REF_CITIES (reference city labels) and VB.

Scale: 897 routes, 61 clusters, 493 places, 1,280 people, 595 of them with
movement (1,277 legs). That's small. If the map feels slow, the cause is
almost certainly how it's drawn, not how much it draws.

## Hard-won rules

1. The data arrays in `index.html` are generated. Regenerate with the
   pipeline and graft. Never hand-edit or string-splice them. (On 2026-09-23
   a splice silently lost to stale duplicate keys and shipped broken data.)
2. Before shipping data changes, run `diff_shipped.py` against the live page.
   Everyone who matched before must still match, and every difference needs
   an explanation.
3. Check in a real browser before pushing: `tools/check_page.py`, then look
   at the screenshot. Checking data alone isn't enough.
4. GEDCOM individual IDs (`@I...@`) are stable across exports. Family IDs
   (`@F...@`) change every export.
5. A GEDCOM person can have several NAME records. A blank one mustn't
   overwrite a real name (this once hid Daniel Baskett from search). Fixed in
   stages 1 and 2.
6. Don't assume. Read the file, run the code, check the output.

## Known issues and state (2026-09-24)

- Four people (Lily Trinder, Clarissa Farmer, James Holt, Margaret Bailey,
  in the Georgia/Alabama cluster) differ slightly from the pre-recovery map
  in intermediate stops. This was accepted.
- Mary Godbey, Henry Baskett and Sarah Trigg have only one place each in
  the tree, so they show as birthplace dots with no journey. That's missing
  data, not a bug. Adding residences in the tree would fix it.
- James finds the map laggy. See `REBUILD_BRIEF.md`.

## Recent research that shaped the current data (context only)

In September 2026 James established, from Cumberland and Goochland County
records, that Thomas Baskett (b. ~1739, d. 1773 Cumberland) was the son of
Daniel Baskett and Mary Godbey. The long-assumed "Thomas Baskett Sr.
(b. 1716)" was removed from the tree; `tools/check_page.py` checks that he
stays gone. The Godbey line runs back to Thomas Godbey Sr., who sailed on the
Sea Venture: Plymouth → Bermuda (wrecked 1609) → Jamestown (1610).
