"""
Screenshot two versions of the map at identical views and measure how much
they differ, pixel by pixel. For checking that a rebuild still looks the same.

Usage:  python tools/compare_views.py OLD_URL NEW_URL OUT_DIR [--dpr 1.5] [--only view1,view2]

For every view it writes OUT_DIR/<view>_old.png, <view>_new.png and
<view>_diff.png over a faded copy of the old image: magenta = a real
difference (nothing similar within 2 px in the other image), pale pink =
the same thing shifted by a pixel or two (anti-aliasing, sub-pixel
placement). It prints both shares. The difference is computed in the
browser, so no image library is needed.
"""
import sys, pathlib, base64, json
from playwright.sync_api import sync_playwright

old_url, new_url, out = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
DPR = float(sys.argv[sys.argv.index('--dpr') + 1]) if '--dpr' in sys.argv else 1
out.mkdir(parents=True, exist_ok=True)
VIEW = {'width': 1500, 'height': 900}

# (name, data-space centre x, y, zoom[, JS to run first]). Coordinates are
# the page's projected units. The last view focuses a thread, which dims
# everything else; it stays last because focus persists.
VIEWS = [('default_1x', None, None, 1),
         ('east_coast_2x', -38.0, 25.0, 2),
         ('virginia_5x', -43.0, 27.5, 5),
         ('virginia_12x', -43.0, 27.5, 12),
         ('new_england_8x', -35.5, 22.5, 8),
         ('dashed_birmingham_40x', -51.87, 31.5, 40),   # back-and-forth (dashed) routes, 19 and 12 ancestors
         ('twin_ithaca_macon_6x', -45.5, 27.8, 6),      # families traveling together (twin strokes)
         ('focus_godbey_2x', -40.0, 25.0, 2,
          "clearFocus(); focusThread(SEARCH_INDEX.find(s => s.name === 'Thomas Godbey Sr.').id)")]

SET_VIEW = """([x, y, k]) => {
  if (x === null) currentTransform = d3.zoomIdentity;
  else {
    const rect = mapWrap.getBoundingClientRect();
    const vx = (rect.width/2 - base.offsetX)/base.scale, vy = (rect.height/2 - base.offsetY)/base.scale;
    currentTransform = d3.zoomIdentity.translate(vx - x*k, vy - y*k).scale(k);
  }
  redrawAll(); updateLabels();
}"""

DIFF = """async ([a, b]) => {
  const load = src => new Promise(r => { const i = new Image(); i.onload = () => r(i); i.src = src; });
  const [A, B] = await Promise.all([load(a), load(b)]);
  const w = A.width, h = A.height, c = document.createElement('canvas'); c.width = w; c.height = h;
  const x = c.getContext('2d');
  x.drawImage(A, 0, 0); const da = x.getImageData(0, 0, w, h).data;
  x.drawImage(B, 0, 0); const db = x.getImageData(0, 0, w, h).data;
  const o = x.createImageData(w, h); let n = 0, real = 0;
  const close = (p, q, j) => Math.max(Math.abs(p[j]-q[j]), Math.abs(p[j+1]-q[j+1]), Math.abs(p[j+2]-q[j+2])) <= 24;
  // does pixel (px,py) of image P have a close match within R px in image Q?
  const R = 2;
  const nearMatch = (P, Q, px, py) => {
    const i = (py * w + px) * 4;
    for (let dy = -R; dy <= R; dy++) for (let dx = -R; dx <= R; dx++) {
      const qx = px + dx, qy = py + dy;
      if (qx < 0 || qy < 0 || qx >= w || qy >= h) continue;
      const j = (qy * w + qx) * 4;
      if (Math.max(Math.abs(P[i]-Q[j]), Math.abs(P[i+1]-Q[j+1]), Math.abs(P[i+2]-Q[j+2])) <= 24) return true;
    }
    return false;
  };
  for (let py = 0; py < h; py++) for (let px = 0; px < w; px++) {
    const i = (py * w + px) * 4;
    if (close(da, db, i)) {
      o.data[i] = o.data[i+1] = o.data[i+2] = 255 - (255 - (da[i]+da[i+1]+da[i+2])/3) * 0.25; o.data[i+3] = 255;
      continue;
    }
    n++;
    // a real difference: something in one image with nothing like it nearby in the other
    const isReal = !nearMatch(da, db, px, py) || !nearMatch(db, da, px, py);
    if (isReal) { real++; o.data[i] = 255; o.data[i+1] = 0; o.data[i+2] = 255; }
    else { o.data[i] = 255; o.data[i+1] = 200; o.data[i+2] = 235; }
    o.data[i+3] = 255;
  }
  x.putImageData(o, 0, 0);
  return { pct: 100 * n / (w * h), real_pct: 100 * real / (w * h), png: c.toDataURL('image/png') };
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pages = {}
    for tag, url in [('old', old_url), ('new', new_url)]:
        pg = b.new_page(viewport=VIEW, device_scale_factor=DPR)
        errs = []; pg.on('pageerror', lambda e, errs=errs: errs.append(str(e)[:200]))
        pg.goto(url); pg.wait_for_function('typeof redrawAll === "function"'); pg.wait_for_timeout(800)
        pages[tag] = (pg, errs)
    diffpage = b.new_page()
    results = []
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
    for name, x, y, k, *pre in VIEWS:
        if only and name not in only: continue
        shots = {}
        for tag, (pg, _) in pages.items():
            if pre: pg.evaluate(pre[0]); pg.wait_for_timeout(200)
            pg.evaluate(SET_VIEW, [x, y, k])
            pg.wait_for_timeout(600)   # let the place-dot fade transitions finish
            shots[tag] = pg.screenshot()
            (out / f'{name}_{tag}.png').write_bytes(shots[tag])
        uri = lambda png: 'data:image/png;base64,' + base64.b64encode(png).decode()
        r = diffpage.evaluate(DIFF, [uri(shots['old']), uri(shots['new'])])
        (out / f'{name}_diff.png').write_bytes(base64.b64decode(r['png'].split(',', 1)[1]))
        results.append((name, r['pct'], r['real_pct']))
        print(f'{name:18} {r["pct"]:6.2f}% of pixels differ; {r["real_pct"]:6.3f}% are more than a {2}px shift')
    for tag, (_, errs) in pages.items():
        if errs: print(f'PAGE ERRORS ({tag}): {errs}')
    b.close()
