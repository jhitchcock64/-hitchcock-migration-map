"""
Frame-time profile of any map page under real mouse gestures: wheel zoom,
pan while zoomed in, pan at the whole-map view. Works on the MapLibre page
(index.html) and on legacy.html alike, since it only drives the mouse and
counts animation frames. (tools/profile_page.py profiles the pre-MapLibre
renderer's internals and only suits legacy.html.)

Setup (once):  pip install playwright && python -m playwright install chromium
Serve first:   python -m http.server 8000     (from the repo root)
Usage:         python tools/profile_gestures.py URL [URL ...] [--reps N]
               e.g. python tools/profile_gestures.py http://localhost:8000/legacy.html http://localhost:8000/

Runs in a real window at 1500x900, device pixel ratio 1.5 (James's laptop).
Plug the laptop in first: on battery Windows throttles the GPU; the script
prints the idle frame interval so a throttled run is obvious (> 17 ms).
A frame counts as dropped when it takes over 1.5x the idle interval.
"""
import sys, time, statistics
from playwright.sync_api import sync_playwright

urls = [a for a in sys.argv[1:] if not a.startswith('--')]
reps = int(sys.argv[sys.argv.index('--reps') + 1]) if '--reps' in sys.argv else 2
if '--reps' in sys.argv: urls.remove(sys.argv[sys.argv.index('--reps') + 1])

# each measurement gets its own frame loop; an older loop still pending stops
# itself (otherwise two loops would record every frame twice)
START = ("() => { window.__f = []; const g = window.__gen = (window.__gen || 0) + 1;"
         " (function l(t) { if (window.__gen !== g) return; __f.push(t); requestAnimationFrame(l); })(performance.now()); }")
STOP = "() => new Promise(r => setTimeout(() => { window.__gen = (window.__gen || 0) + 1; r(__f); }, 400))"


def stats(frames, idle):
    d = sorted(b - a for a, b in zip(frames, frames[1:]))
    if not d: return 'no frames'
    dropped = sum(x > idle * 1.5 for x in d)
    return (f'frames {len(d):4}  median {statistics.median(d):5.1f}  p95 {d[int(len(d) * .95)]:6.1f}'
            f'  max {d[-1]:6.1f}  dropped {100 * dropped // len(d):3}%')


def paced(n, dt, fn):
    t0 = time.perf_counter()
    for i in range(n):
        fn(i)
        w = t0 + (i + 1) * dt - time.perf_counter()
        if w > 0: time.sleep(w)


args = ['--disable-renderer-backgrounding', '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows', '--disable-features=CalculateNativeWinOcclusion']
with sync_playwright() as p:
    b = p.chromium.launch(headless=False, args=args)
    pg = b.new_page(viewport={'width': 1500, 'height': 900}, device_scale_factor=1.5)
    pg.goto('about:blank')
    fr = pg.evaluate("() => new Promise(r => { const f = []; const t0 = performance.now();"
                     " (function t(x) { f.push(x); if (x - t0 < 1500) requestAnimationFrame(t); else r(f); })(t0); })")
    idle = statistics.median([b2 - a for a, b2 in zip(fr[1:], fr[2:])])
    print(f'idle frame {idle:.1f} ms' + ('' if idle < 18 else '  <-- throttled (on battery?)'))
    for url in urls:
        print('==', url)
        for rep in range(reps):
            pg.goto(url); pg.wait_for_timeout(6000)        # let the page, tiles and data settle
            cx, cy = 560, 560                               # ~ Virginia in both pages' default views
            pg.mouse.move(cx, cy)
            pg.evaluate(START)
            paced(70, 1 / 60, lambda i: pg.mouse.wheel(0, -40))
            pg.wait_for_timeout(1500)
            print('  zoom in     ', stats(pg.evaluate(STOP), idle))
            pg.evaluate(START)
            pg.mouse.move(1100, 500); pg.mouse.down()
            paced(90, 1 / 60, lambda i: pg.mouse.move(1100 - 800 * (i + 1) / 90, 500 - 150 * (i + 1) / 90))
            pg.mouse.up(); pg.wait_for_timeout(800)
            print('  pan zoomed  ', stats(pg.evaluate(STOP), idle))
            paced(70, 1 / 60, lambda i: pg.mouse.wheel(0, 40)); pg.wait_for_timeout(2500)
            pg.evaluate(START)
            pg.mouse.move(1100, 500); pg.mouse.down()
            paced(90, 1 / 60, lambda i: pg.mouse.move(1100 - 800 * (i + 1) / 90, 500 - 150 * (i + 1) / 90))
            pg.mouse.up(); pg.wait_for_timeout(800)
            print('  pan whole   ', stats(pg.evaluate(STOP), idle))
    b.close()
