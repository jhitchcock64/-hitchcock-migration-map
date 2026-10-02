"""
Smoke test for the extended data (data_ext.js): opens the map, tree, People and Ask pages as a cousin
("Viewing as" a child of Joy Marie Howard and Thomas Clay Baskett Jr.) and checks that the pages load
the extended file, start from that family, and draw their routes. Then checks that going back to the
default drops the extended file again.

Usage:  python tools/check_ext.py [--shot out.png]
"""
import json, pathlib, sys
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
shot = sys.argv[sys.argv.index('--shot') + 1] if '--shot' in sys.argv else None
problems = []

with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 1500, 'height': 900}); pg = ctx.new_page()
    errors = []; pg.on('pageerror', lambda e: errors.append(str(e)[:300]))
    pg.goto((ROOT / 'index.html').as_uri())
    pg.wait_for_function("typeof Viewer !== 'undefined'")
    core = pg.evaluate("Object.keys(GRAPH.people).length")
    # choose the cousin; the page reloads itself with the extended data
    pg.evaluate("(async () => { await Viewer.load(); const k = RELATIVES.n.indexOf('Joy Marie Howard'); setTimeout(() => Viewer.choose(k, 1, null), 50); })()")
    pg.wait_for_function("window.HM_EXT === true && typeof GRAPH !== 'undefined' && typeof Ask !== 'undefined'", timeout=30000)
    v = json.loads(pg.evaluate("localStorage.getItem('hm-viewer')"))
    ext = pg.evaluate("Object.keys(GRAPH.people).length")
    print(f'core {core} people; as a cousin {ext}; starts from {pg.evaluate("GRAPH.people[Viewer.mapId()].name")}')
    if not v.get('ext') or ext <= core: problems.append('the extended data did not load for a cousin')
    ans = pg.evaluate("(async () => { const d = document.createElement('div'); d.innerHTML = await Ask.answer('How am I related to Daniel Baskett?'); return d.innerText.slice(0, 90); })()")
    print('ask:', ans.replace('\n', ' '))
    if '6th great-grandfather' not in ans: problems.append('Ask: Daniel Baskett should be a 6th great-grandfather')

    pg.goto((ROOT / 'map.html').as_uri())
    pg.wait_for_function("typeof mapReady !== 'undefined' && mapReady && map.loaded()", timeout=40000)
    pg.wait_for_timeout(2500)
    r = pg.evaluate("""() => ({ ext: window.HM_EXT, target: GRAPH.people[CURRENT_TARGET].name, anc: TARGET_ANCESTOR_SET.size,
        relevant: ROUTES.filter(isRouteRelevant).length,
        drawn: map.queryRenderedFeatures({ layers: ['routes-plain', 'bundles', 'clusters'].filter(l => map.getLayer(l)) }).length,
        both: [...TARGET_ANCESTOR_SET].some(x => /Howard/.test(GRAPH.people[x].name)) && [...TARGET_ANCESTOR_SET].some(x => GRAPH.people[x].name === 'Daniel Baskett') })""")
    print('map:', r)
    if shot: pg.screenshot(path=shot)
    if not (r['ext'] and r['both'] and r['relevant'] > 50 and r['drawn'] > 0): problems.append('map: the cousin\'s routes are not drawn')

    pg.goto((ROOT / 'tree.html').as_uri()); pg.wait_for_timeout(1500)
    t = pg.evaluate("GRAPH.people[root].name"); print('tree root:', t)
    pg.goto((ROOT / 'people.html').as_uri()); pg.wait_for_timeout(1500)
    n = pg.evaluate("document.querySelectorAll('.row').length"); print('people rows:', n)
    if n <= core - 20: problems.append('People: the extended people are not listed')

    # back to the default: the core file again
    pg.goto((ROOT / 'index.html').as_uri()); pg.wait_for_function("typeof Viewer !== 'undefined'")
    pg.evaluate("setTimeout(() => Viewer.set(null), 50)")
    pg.wait_for_function("window.HM_EXT === false && typeof GRAPH !== 'undefined'", timeout=30000)
    back = pg.evaluate("Object.keys(GRAPH.people).length"); print('back to the default:', back, 'people')
    if back != core: problems.append('the default did not come back')
    b.close()
if errors: problems.append(f'page errors: {errors[:3]}')
print('\nFAIL: ' + '; '.join(problems) if problems else '\nPASS')
sys.exit(1 if problems else 0)
