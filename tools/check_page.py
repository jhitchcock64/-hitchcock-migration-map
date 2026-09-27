"""
Smoke test for the map page. Loads it in headless Chromium and checks that it
renders without errors and that key people and routes are present.

Setup (once):  pip install playwright && python -m playwright install chromium
Usage:         python tools/check_page.py [path/to/index.html] [--shot out.png]
               (works on index.html and on legacy.html, the pre-rebuild page)
Exit code 0 = all checks passed.
"""
import sys, pathlib, json
from playwright.sync_api import sync_playwright

args = [a for a in sys.argv[1:] if not a.startswith('--')]
page_path = pathlib.Path(args[0] if args else 'index.html').resolve()
shot = sys.argv[sys.argv.index('--shot') + 1] if '--shot' in sys.argv else None

CHECKS = """() => {
  const out = {};
  out.routes = ROUTES.length; out.clusters = CLUSTERS.length; out.places = PLACES.length;
  out.people = Object.keys(GRAPH.people).length; out.with_legs = Object.keys(PERSON_LEGS).length;
  let broken = 0; for (const r of ROUTES) for (const a of (r.anchor_ids||[])) if (!GRAPH.people[a]) broken++;
  out.broken_anchors = broken;
  const byName = n => SEARCH_INDEX.filter(s => s.name === n).map(s => s.id);
  const legs = id => (PERSON_LEGS[id]||[]).map(l => l.from + ' -> ' + l.to);
  const d = byName('Daniel Baskett')[0], g = byName('Thomas Godbey Sr.')[0];
  out.daniel_legs = d ? legs(d) : null;
  out.godbey_sr_legs = g ? legs(g) : null;
  const t = GRAPH.people['@I240024526662@'];
  out.thomas_1739_parents = t ? t.parents.map(p => GRAPH.people[p] && GRAPH.people[p].name) : null;
  out.phantom_thomas_sr_1716 = SEARCH_INDEX.some(s => s.name.startsWith('Thomas Baskett') && s.birt === '1716');
  out.year_range = [Math.floor(YEAR_MIN), Math.ceil(YEAR_MAX)];
  // military service (MILITARY, from pipeline/military/itineraries.py)
  out.military = typeof MILITARY === 'undefined' ? null : {
    people: Object.keys(MILITARY).length,
    routed: Object.values(MILITARY).flat().filter(e => e.legs.length).length,
    missing_people: Object.keys(MILITARY).filter(id => !GRAPH.people[id]).length,
    worthington_stops: (MILITARY['@I242209901667@'] || [{stops: []}])[0].stops.map(s => s.l.split(' (')[0]) };
  out.notable = typeof NOTABLE === 'undefined' ? null : {
    events: NOTABLE.events.length, arrivals: NOTABLE.events.filter(e => e.k === 'arrival').length,
    missing_people: NOTABLE.events.filter(e => e.p.some(id => !GRAPH.people[id])).length,
    godspeed: NOTABLE.events.some(e => e.sh === 'Godspeed') };
  out.title = document.title;
  // something was actually drawn: route features on the MapLibre map
  // (index.html), or routes the Canvas 2D renderer stroked (legacy.html)
  const ml = typeof map !== 'undefined' && map && typeof map.getSource === 'function';
  out.renderer = ml ? 'maplibre' : 'canvas2d';
  out.routes_drawn = ml ? map.queryRenderedFeatures({ layers: ['routes-plain', 'routes-osc', 'routes-family1', 'clusters', 'bundles'].filter(l => map.getLayer(l)) }).length
                        : ROUTES.filter(r => r._screen).length;
  return out;
}"""

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1500, 'height': 900})
    errors = []; pg.on('pageerror', lambda e: errors.append(str(e)[:300]))
    pg.goto(page_path.as_uri())
    # the MapLibre page draws once its style and tiles have loaded (up to ~20 s on a slow link)
    pg.wait_for_function("typeof mapReady === 'undefined' || (mapReady && map.loaded())", timeout=30000)
    pg.wait_for_timeout(2500)
    r = pg.evaluate(CHECKS)
    if shot: pg.screenshot(path=shot)
    # profiles: profiles.js loads and a known ancestor's opens with its sections (MapLibre page only)
    r['profile'] = pg.evaluate('''typeof openProfile !== 'function' ? null : openProfile('@I242209901667@').then(() => ({
        name: (document.querySelector('#profile h2') || {}).textContent,
        sections: [...document.querySelectorAll('#profile .pf-eyebrow')].map(e => e.textContent),
        people: typeof PROFILES === 'undefined' ? 0 : Object.keys(PROFILES.people).length }))''')
    b.close()

print(json.dumps(r, indent=1))
problems = []
if errors: problems.append(f'page errors: {errors}')
if r['broken_anchors']: problems.append(f"{r['broken_anchors']} routes point at people missing from GRAPH")
if not r['daniel_legs'] or 'Goochland' not in ' '.join(r['daniel_legs']): problems.append('Daniel Baskett missing or has no Goochland leg')
if not r['godbey_sr_legs'] or 'Bermuda' not in ' '.join(r['godbey_sr_legs']): problems.append('Thomas Godbey Sr. voyage via Bermuda missing')
if r['thomas_1739_parents'] != ['Daniel Baskett', 'Mary Godbey']: problems.append(f"Thomas Baskett (1739) parents wrong: {r['thomas_1739_parents']}")
if r['phantom_thomas_sr_1716']: problems.append('phantom Thomas Baskett Sr. (b.1716) is back in search')
if not r['routes_drawn']: problems.append('no routes were drawn')
if r['renderer'] == 'maplibre':
    m = r.get('military')
    if not m: problems.append('MILITARY missing from data.js')
    else:
        if m['missing_people']: problems.append(f"{m['missing_people']} military entries point at people missing from GRAPH")
        if m['routed'] < 20: problems.append(f"only {m['routed']} military services have routes")
        if 'Montreal' not in m['worthington_stops']: problems.append("William Worthington's captivity (Montreal) missing from MILITARY")
    n = r.get('notable')
    if not n: problems.append('NOTABLE missing from data.js')
    else:
        if n['missing_people']: problems.append(f"{n['missing_people']} notable events point at people missing from GRAPH")
        if n['arrivals'] < 50: problems.append(f"only {n['arrivals']} arrivals in NOTABLE")
        if not n['godspeed']: problems.append('the Godspeed landing is missing from NOTABLE')
    if r.get('title') != 'Family History, Visualized': problems.append(f"page title is {r.get('title')!r}")
    pf = r.get('profile')
    if pf is not None:
        if pf['name'] != 'William Worthington' or 'Timeline' not in pf['sections']: problems.append(f'profile panel broken: {pf}')
        if pf['people'] < 1200: problems.append(f"only {pf['people']} profiles in profiles.js")
print('\nPASS' if not problems else '\nFAIL:\n  ' + '\n  '.join(problems))
sys.exit(1 if problems else 0)
