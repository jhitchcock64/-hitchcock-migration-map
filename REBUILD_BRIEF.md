# Task: make the migration map fast

You're picking up the Hitchcock migration map. Read `CLAUDE.md` first (it
should already be loaded) and `pipeline/RUNBOOK.md` if you touch data.

**Goal:** James finds the live map laggy. Make zooming, panning, hovering and
switching modes feel instant, without losing any feature or changing how the
map looks, unless James approves the change.

**How to work:** Go phase by phase. At each **CHECKPOINT**, stop, report
briefly with numbers and screenshots, and wait for James before continuing.
Keep the live site untouched until the final phase. Commit work on a branch
(`rebuild`), not `main`.

---

## Phase 0: Setup and sanity (no checkpoint unless something fails)

1. `git checkout -b rebuild`
2. Install the test tooling:
   `pip install playwright && python -m playwright install chromium`
3. Serve the repo locally: `python3 -m http.server 8000` (in the background).
4. Run `python tools/check_page.py index.html`. It must print PASS.
5. You don't need the GEDCOM for this task. All the data is already in
   `index.html`.

## Phase 1: Measure (CHECKPOINT)

Find out where the time actually goes before changing anything. Write
`tools/profile_page.py` (Playwright) to measure the current page:

- Load: time to first paint and to first route drawn, and how long parsing
  the ~1.9 MB of inline data takes.
- Zoom: frame times while zooming in step by step from 1× to 20× with the
  wheel, centered on Virginia. Report the median and 95th-percentile frame
  times and dropped frames.
- Pan: frame times while dragging across the Atlantic at zoom 1× and at 8×.
- Hover: time from mousemove to tooltip over a dense area (Virginia /
  Kentucky).
- Mode switches: time for `setTarget` on Margaret (default), on a deep
  ancestor, and on Thomas Godbey Sr.; frame times during Time period
  playback.
- Break frame time down by function using a Chrome performance trace
  (Playwright CDP `Tracing`) or `performance.now()` instrumentation injected
  at runtime (never edit the live file for this).

Suspects from reading the code, to confirm or rule out:
- `redrawAll()` updates the transform on SVG basemap paths every frame
  (`land_near` is ~324 KB of path data), which forces the browser to
  rasterize them again.
- It also writes the `r` attribute on ~500 SVG place dots every frame.
- `drawRoutes()` filters and sorts all 897 routes, rebuilds screen points,
  and strokes curves, twin strokes and arrowheads on Canvas 2D every frame.
- Label layout (`updateLabels`) during gestures.
- Hover hit-testing is a linear scan over every route and cluster.
- There are only 897 routes. If Canvas 2D alone is slow at this size, look
  for waste rather than blaming scale.

Report: a short table of the numbers, the top three costs with evidence, and
a recommendation (next phase).

## Phase 2: Choose the approach (CHECKPOINT)

Using Phase 1's evidence, recommend one of these, with the expected gain:

- **A. Targeted fixes to the current page.** For example: draw the basemap
  once into a cached bitmap per zoom band and transform the bitmap during
  gestures; draw place dots on canvas; cache each route as a `Path2D` in
  data coordinates and apply the zoom via `ctx.setTransform` so nothing is
  re-projected per frame; filter and sort only when the target or mode
  changes; add a spatial index for hover (e.g. flatbush); skip label layout
  mid-gesture.
- **B. New renderer.** deck.gl with an `OrthographicView` over the existing
  projected coordinates keeps the current look and needs no reprojection.
  Alternatively MapLibre GL + deck.gl on a real basemap. Routes would use
  `PathLayer` (bow arcs pre-sampled to points), places `ScatterplotLayer`,
  labels `TextLayer`, and picking would be GPU-based.

Prefer A if Phase 1 shows it gets most of the way. It carries far less risk
of losing features. Whatever you choose, stay within these limits:
- Static hosting on GitHub Pages: no server, no paid services, no API keys.
- No new external runtime dependency without James's approval. Self-hosting
  a library in the repo is fine.
- The look stays the same: parchment basemap, typography, the 7-stop
  rank-based color scale, route widths, twin and dashed styles, arrowheads.
- It must still work on phones and tablets (touch pan and pinch).

## Phase 3: Prototype (CHECKPOINT)

- Build the prototype **alongside** the live page: `v2/index.html` (and
  `v2/*.js`, `v2/data/*.json` if data leaves the HTML). Don't modify the
  root `index.html`.
- If data moves out of the HTML, write `tools/export_data.py` to pull the
  arrays out of `index.html` into `v2/data/`. Later, the pipeline should
  write them directly (Phase 5).
- The prototype must: draw all routes and clusters with correct colors,
  widths and styles; zoom and pan; switch aggregation at the threshold;
  and show hover tooltips.
- Rerun the Phase 1 profile against `v2/` and compare side by side. Take
  screenshots of both at the same view.
- Tell James how to open it locally so he can feel the difference.

## Phase 4: Feature parity (CHECKPOINT after each group)

Port the features in groups, checking each against the live page with
screenshots at matching views. Checklist:

- [ ] Default view: Family journey to Margaret, with all ancestor routes
- [ ] Colors, widths, twin strokes, dashes, arrowheads, cluster bands below
      zoom 4.5 with the ancestor counts shown in tooltips
- [ ] Basemap: land, state borders, lakes, rivers, the detail swap on zoom
- [ ] Place dots, place labels by tier without collisions, reference-city
      labels, the convergence ring and label at the target
- [ ] Legend (gradient painted from the color function; derive the
      min/median/max labels and the header years from the data)
- [ ] Search in each mode
- [ ] Family journey: set any person as target; routes update; cluster
      counts update
- [ ] Life journey
- [ ] Path between two people, with status text
- [ ] Time period: from/to inputs, playback from 1545 to 2026 in 2-year
      steps every 200 ms, and the person filter chip
- [ ] Surname filter
- [ ] Hover tooltips: single route, cluster, and several overlapping routes
- [ ] Click: route picker for overlaps; focus thread panel with dropdown;
      clear
- [ ] Zoom buttons, zoom level readout, wheel, pinch, drag; the zoom range
      stays 1–60×
- [ ] `tools/check_page.py` updated to run against v2 and passing,
      including the key people (Daniel Baskett, Thomas Godbey Sr.'s voyage
      via Bermuda, Thomas Baskett's parents, no phantom Thomas Sr.)

## Phase 5: Cutover (CHECKPOINT before pushing)

- Update the pipeline's final step so it writes the v2 data format directly
  (replacing `graft.py` for v2), and update `diff_shipped.py` to read it.
  Prove it end to end: GEDCOM → pipeline → v2 data identical to the export
  from Phase 3.
- Move the old page to `legacy.html` (keep it reachable) and make v2 the
  root `index.html`.
- Update `CLAUDE.md` (architecture section) and `pipeline/RUNBOOK.md`.
- Final profile numbers compared with the Phase 1 baseline.
- Merge to `main` and push only after James approves.
