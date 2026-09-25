"""
Feature-parity check: perform the same searches and mode switches on two
versions of the map and compare what each shows at every step.

Usage:  python tools/parity_check.py OLD_URL NEW_URL [OUT_DIR]

At each step it records the page's visible state -- search results, page
title, focus panel (title, summary, every row of the moves dropdown), path
status, era inputs and person-filter chip, zoom, and every cluster's
ancestor count -- and reports any difference. With OUT_DIR it also saves
a screenshot of each step from both pages (<step>_old.png, <step>_new.png).
Exit code 0 = no differences.
"""
import sys, json, pathlib
from playwright.sync_api import sync_playwright

OLD, NEW = sys.argv[1], sys.argv[2]
OUT = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else None
if OUT: OUT.mkdir(parents=True, exist_ok=True)

STATE = """() => {
  const txt = sel => { const e = document.querySelector(sel); return e ? e.innerText.trim() : null; };
  const vis = sel => { const e = document.querySelector(sel); return !!e && getComputedStyle(e).display !== 'none'
                       && (!e.classList.length || !['search-results','era-person-results','focus-dropdown','path-status','focus-panel']
                            .some(id => e.id === id) || e.classList.contains('active')); };
  return {
    title: document.title,
    heading: txt('#page-title'),
    results: vis('#search-results') ? [...document.querySelectorAll('#search-results .sr-item, #search-results .sr-empty')].map(e => e.innerText.trim()) : [],
    eraResults: vis('#era-person-results') ? [...document.querySelectorAll('#era-person-results .sr-item')].map(e => e.innerText.trim()) : [],
    focusActive: document.getElementById('focus-panel').classList.contains('active'),
    focusTitle: txt('#focus-title'), focusSub: txt('#focus-sub'),
    moves: [...document.querySelectorAll('#focus-dropdown .move-row')].map(e => e.innerText.trim()),
    pathStatus: document.getElementById('path-status').classList.contains('active') ? txt('#path-status') : null,
    mode: (document.querySelector('.mode-btn.active') || {}).dataset?.mode,
    yearFrom: document.getElementById('year-from').value, yearTo: document.getElementById('year-to').value,
    chip: getComputedStyle(document.getElementById('era-person-chip')).display !== 'none' ? txt('#era-person-chip-name') : null,
    placeholder: document.getElementById('search-input').placeholder,
    zoom: +currentTransform.k.toFixed(3), tx: +currentTransform.x.toFixed(3), ty: +currentTransform.y.toFixed(3),
    clusters: CLUSTERS.map(c => c._visCount),
    target: CURRENT_TARGET,
  };
}"""


def run(url):
    states, errors = [], []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1500, 'height': 900}, device_scale_factor=1)
        pg.on('pageerror', lambda e: errors.append(str(e)[:200]))
        pg.goto(url); pg.wait_for_function('typeof redrawAll === "function"'); pg.wait_for_timeout(1000)
        tag = 'old' if url == OLD else 'new'

        def snap(step):
            pg.wait_for_timeout(700)
            s = pg.evaluate(STATE); s['step'] = step
            states.append(s)
            if OUT: pg.screenshot(path=str(OUT / f'{step}_{tag}.png'))

        def mode(m): pg.click(f'.mode-btn[data-mode="{m}"]'); pg.wait_for_timeout(200)
        def search(q, pick=None, sel='#search-input', results='#search-results'):
            pg.fill(sel, ''); pg.type(sel, q, delay=20); pg.wait_for_timeout(300)
            if pick is not None:
                items = pg.query_selector_all(f'{results} .sr-item')
                texts = [i.inner_text() for i in items]
                idx = next(i for i, t in enumerate(texts) if t.startswith(pick))
                items[idx].click()

        snap('00_default')
        # --- Family journey: search, then set a new target
        search('godbey'); snap('01_target_search_results')
        pg.click('#page-title')   # close the results without choosing
        search('Godbey', pick='Thomas Godbey Sr.'); snap('02_target_godbey')
        search('Margaret Jean', pick='Margaret Jean Hitchcock'); snap('03_target_back_to_margaret')
        search('zzqx'); snap('04_search_no_match')
        pg.fill('#search-input', ''); pg.click('#page-title')
        # --- Life journey
        mode('life'); snap('10_life_mode')
        search('Daniel Baskett', pick='Daniel Baskett'); snap('11_life_daniel')
        search('Mary Godbey', pick='Mary Godbey'); snap('12_life_mary_single_place')
        pg.click('#focus-sub'); snap('13_life_dropdown_toggle')
        pg.click('#focus-clear'); snap('14_life_cleared')
        # --- Path between
        mode('path'); snap('20_path_mode')
        search('Godbey', pick='Thomas Godbey Sr.'); snap('21_path_first_picked')
        search('Margaret Jean', pick='Margaret Jean Hitchcock'); snap('22_path_result')
        pg.click('#focus-clear')
        # --- Time period
        mode('era'); snap('30_era_mode')
        pg.fill('#year-from', '1600'); pg.fill('#year-to', '1700'); pg.press('#year-to', 'Enter'); snap('31_era_1600_1700')
        search('Daniel Baskett', pick='Daniel Baskett', sel='#era-person-input', results='#era-person-results'); snap('32_era_person_filter')
        pg.click('#era-person-chip .chip-clear'); snap('33_era_filter_cleared')
        pg.fill('#year-from', '1850'); pg.fill('#year-to', '1800'); pg.press('#year-to', 'Enter'); snap('34_era_reversed_bounds')
        # playback: start, let it run ~2 s, pause; record where it stopped
        pg.click('#era-play-btn'); pg.wait_for_timeout(2100); pg.click('#era-play-btn'); snap('35_era_playback_paused')
        # where playback stops depends on timing (headless WebGL runs in software);
        # set fixed years so the later steps compare exactly
        pg.fill('#year-from', '1700'); pg.fill('#year-to', '1750'); pg.press('#year-to', 'Enter'); snap('36_era_after_playback')
        pg.click('#focus-clear')
        # --- Surname
        mode('surname'); snap('40_surname_mode')
        pg.fill('#surname-input', 'Baskett'); pg.press('#surname-input', 'Enter'); snap('41_surname_baskett')
        pg.fill('#surname-input', 'Zzqx'); pg.press('#surname-input', 'Enter'); snap('42_surname_no_match')
        pg.click('#focus-clear'); mode('target')

        # --- interaction: zoom buttons, wheel limits, drag, pinch, clicks
        pg.click('#zoomReset'); pg.wait_for_timeout(300)
        rect = pg.evaluate('(() => { const r = mapWrap.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()')
        cx, cy = rect[0] + rect[2] / 2, rect[1] + rect[3] / 2
        pg.click('#zoomIn'); pg.click('#zoomIn'); snap('50_zoom_buttons_in_x2')
        pg.click('#zoomOut'); snap('51_zoom_button_out')
        pg.click('#zoomReset'); snap('52_zoom_reset')
        pg.mouse.move(cx, cy)
        for _ in range(60): pg.mouse.wheel(0, -300)
        snap('53_wheel_to_max')         # must stop at 60x
        for _ in range(60): pg.mouse.wheel(0, 300)
        snap('54_wheel_to_min')         # must stop at 1x
        pg.mouse.move(cx, cy); pg.mouse.down(); pg.mouse.move(cx - 200, cy - 80, steps=10); pg.mouse.up()
        snap('55_drag')
        # pinch: two touches moving apart, sent as real touch events
        pg.click('#zoomReset'); pg.wait_for_timeout(300)
        cdp = pg.context.new_cdp_session(pg)
        def touch(kind, pts):
            cdp.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': [{'x': x, 'y': y, 'id': i} for i, (x, y) in enumerate(pts)]})
        touch('touchStart', [(cx - 40, cy), (cx + 40, cy)])
        for d in range(40, 201, 20): touch('touchMove', [(cx - d, cy), (cx + d, cy)]); pg.wait_for_timeout(20)
        touch('touchEnd', [])
        snap('56_pinch_zoom')
        # click a single route: the middle of the thickest route that nothing else crosses there
        pg.click('#zoomReset'); pg.wait_for_timeout(300)
        pt = pg.evaluate("""() => {
          if (window.ensureScreenCache) ensureScreenCache();
          const r = mapWrap.getBoundingClientRect();
          const shown = ROUTES.filter(x => x._screen);
          const near = (px, py, route) => shown.filter(o => o !== route && o._screen.some(([x, y]) => Math.hypot(x - px, y - py) < 25)).length;
          for (const route of shown.slice().sort((a, b) => b.count - a.count)) {
            const p = route._screen[5];
            if (p[0] > 250 && p[0] < r.width - 80 && p[1] > 120 && p[1] < r.height - 300 && near(p[0], p[1], route) === 0)
              return [p[0] + r.left, p[1] + r.top];
          }
          return null; }""")
        if pt: pg.mouse.click(*pt)
        snap('57_click_single_route')
        pg.click('#focus-sub'); snap('58_focus_dropdown_open')
        pg.click('#focus-clear'); snap('59_focus_cleared')
        # click where several routes overlap (at 6x, individual routes): the route picker
        pg.evaluate("""() => { const rect = mapWrap.getBoundingClientRect(), k = 6, x = -41.6, y = 27.8;
          const vx = (rect.width/2 - base.offsetX)/base.scale, vy = (rect.height/2 - base.offsetY)/base.scale;
          currentTransform = d3.zoomIdentity.translate(vx - x*k, vy - y*k).scale(k); (window.renderNow || redrawAll)(); }""")
        pg.wait_for_timeout(300)
        pt = pg.evaluate("""() => {
          if (window.ensureScreenCache) ensureScreenCache();
          const r = mapWrap.getBoundingClientRect(), shown = ROUTES.filter(x => x._screen);
          let best = null, bestN = 1;
          for (const route of shown) for (const p of route._screen) {
            if (p[0] < 300 || p[0] > r.width - 100 || p[1] < 150 || p[1] > r.height - 150) continue;
            const n = shown.filter(o => o._screen.some(([x, y], i, a) => i && Math.hypot(x - p[0], y - p[1]) < 6)).length;
            if (n > bestN && n < 6) { bestN = n; best = p; }
          }
          return best && [best[0] + r.left, best[1] + r.top]; }""")
        if pt: pg.mouse.click(*pt)
        snap('60_click_overlap_picker')
        picker = pg.evaluate("[...document.querySelectorAll('#route-picker.active .picker-row')].map(e => e.innerText.trim())")
        states[-1]['pickerRows'] = picker
        if picker: pg.click('#route-picker .picker-row'); snap('61_picker_choose_first')
        pg.click('#focus-clear')
        # click a cluster band at 2x: zooms in past the aggregation threshold
        pg.evaluate("""() => { const rect = mapWrap.getBoundingClientRect(), k = 2, x = -45, y = 29;
          const vx = (rect.width/2 - base.offsetX)/base.scale, vy = (rect.height/2 - base.offsetY)/base.scale;
          currentTransform = d3.zoomIdentity.translate(vx - x*k, vy - y*k).scale(k); (window.renderNow || redrawAll)(); }""")
        pg.wait_for_timeout(300)
        pt = pg.evaluate("""() => {
          if (window.ensureScreenCache) ensureScreenCache();
          const r = mapWrap.getBoundingClientRect();
          const c = CLUSTERS.filter(c => c._screen).sort((a, b) => b._visCount - a._visCount)[0];
          if (!c) return null; const p = c._screen[5]; return [p[0] + r.left, p[1] + r.top]; }""")
        if pt: pg.mouse.click(*pt)
        snap('62_click_cluster_zooms_in')
        b.close()
    return states, errors


old, oerr = run(OLD)
new, nerr = run(NEW)
problems = 0
for a, b in zip(old, new):
    diffs = {k: (a[k], b[k]) for k in a if a[k] != b[k]}
    # playback timing can differ by a tick between two runs
    if a['step'].startswith('35') and 'yearFrom' in diffs:
        if abs(int(a['yearFrom'] or 0) - int(b['yearFrom'] or 0)) <= 6:
            print(f"note {a['step']}: playback paused at {a['yearFrom']} (old) vs {b['yearFrom']} (new) -- timing, tolerated")
            for k in ('yearFrom', 'yearTo', 'focusTitle', 'focusSub', 'moves', 'zoom', 'tx', 'ty'): diffs.pop(k, None)
    if diffs:
        problems += 1
        print(f"DIFF {a['step']}:")
        for k, (x, y) in diffs.items():
            print(f'   {k}:\n      old {json.dumps(x)[:300]}\n      new {json.dumps(y)[:300]}')
    else:
        extra = f" | {a['focusTitle']} | {a['focusSub']}" if a['focusActive'] else ''
        print(f"same {a['step']:28} zoom {a['zoom']}{extra}"[:170])
for tag, errs in (('old', oerr), ('new', nerr)):
    if errs: print(f'PAGE ERRORS ({tag}):', errs); problems += 1
print('\nPASS' if not problems else f'\n{problems} step(s) differ')
sys.exit(1 if problems else 0)
