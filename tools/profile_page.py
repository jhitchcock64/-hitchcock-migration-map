"""
Performance profile of the map page. Loads it in Chromium (via Playwright),
drives zoom / pan / hover / mode switches, and reports frame times plus a
breakdown of where the time goes. Nothing is written to the page file:
timing wrappers are injected at runtime.

Setup (once):  pip install playwright && python -m playwright install chromium
Serve first:   python -m http.server 8000     (from the repo root)
Usage:         python tools/profile_page.py [URL] [--headed] [--dpr 1.5]
                   [--ablate] [--json out.json] [--shots DIR]

  URL        default http://localhost:8000/index.html
  --headed   real window with the real GPU (closer to what a person feels);
             default is headless
  --dpr N    device pixel ratio (a laptop at 150% scaling is 1.5)
  --ablate   rerun zoom and pan with one layer switched off at a time
             (basemap, place dots, labels, routes) to show what each costs
  --ablate stack   instead add layers one at a time to an empty map
  --reps N   repetitions per ablation variant (default 3)
  --skip-main  with --ablate, skip the main scenarios and run only ablations
  --json     also write every number to a JSON file
  --shots    save a screenshot after each scenario into DIR

Frame times come from requestAnimationFrame timestamps. The script first
measures the idle frame interval on a blank page (16.7 ms at 60 Hz; longer
when a laptop on battery throttles its GPU -- plug in before profiling). A
"dropped" frame is any interval over 1.5x that idle interval.
The function and browser-phase breakdowns come from a Chrome trace.
"""
import sys, json, time, statistics, pathlib, re
from collections import defaultdict
from playwright.sync_api import sync_playwright

args = [a for a in sys.argv[1:] if not a.startswith('--')]
def opt(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
URL = next((a for a in args if a.startswith('http') or a.endswith('.html')), 'http://localhost:8000/index.html')
if URL.endswith('.html') and not URL.startswith('http'):
    URL = pathlib.Path(URL).resolve().as_uri()
HEADED = '--headed' in sys.argv
DPR = float(opt('--dpr', 1))
ABLATE = '--ablate' in sys.argv
SKIP_MAIN = '--skip-main' in sys.argv
JSON_OUT = opt('--json')
SHOTS = opt('--shots')
# option values are not URLs; drop them from positional detection
VIEW = {'width': 1500, 'height': 900}

# Functions whose time we record. Top-level function declarations in the
# page are properties of window, and calls between them resolve through the
# global object, so replacing window[name] catches internal calls too.
WRAP = ['redrawAll', 'drawRoutes', 'drawThread', 'updateLabels', 'positionConvLabel',
        'applyZoomAt', 'doHover', 'handleClick', 'setTarget', 'recomputeClusterVisibility',
        'applyYearRange', 'computeYearRangeSegs', 'zoomToFitSegs', 'renderFocusedChain',
        'buildFocusDropdown', 'focusThread', 'runSearch',
        'gestureFrame', 'settle', 'renderNow']   # v2 only (in v2, redrawAll only schedules renderNow)

INSTRUMENT = """(names) => {
  const P = window.__prof = { calls: {}, frames: [], rec: false };
  for (const n of names) {
    const f = window[n];
    if (typeof f !== 'function') continue;
    window[n] = function (...a) {
      const t0 = performance.now();
      try { return f.apply(this, a); }
      finally { if (P.rec) (P.calls[n] ||= []).push(performance.now() - t0); }
    };
  }
  const loop = (t) => { if (P.rec) P.frames.push(t); requestAnimationFrame(loop); };
  requestAnimationFrame(loop);
  // mousemove -> tooltip latency: stamp every trusted mousemove, and when the
  // tooltip's content or opacity changes, record the time since the last one
  P.lastMove = 0; P.tipLat = [];
  window.addEventListener('mousemove', e => { P.lastMove = performance.now(); }, true);
  const tip = document.getElementById('tooltip');
  new MutationObserver(() => {
    if (P.rec && P.lastMove) P.tipLat.push(performance.now() - P.lastMove);
  }).observe(tip, { attributes: true, childList: true, subtree: true, characterData: true });
}"""

START = "() => { const P = window.__prof; P.calls = {}; P.frames = []; P.tipLat = []; P.rec = true; }"
STOP = """() => new Promise(res => requestAnimationFrame(() => requestAnimationFrame(() => {
  const P = window.__prof; P.rec = false;
  res({ calls: P.calls, frames: P.frames, tipLat: P.tipLat });
})))"""

TRACE_CATS = ['devtools.timeline', 'disabled-by-default-devtools.timeline',
              'disabled-by-default-devtools.timeline.frame', 'blink', 'cc', 'gpu',
              'v8', 'v8.execute', 'toplevel', 'disabled-by-default-v8.compile']


def pct(xs, p):
    if not xs: return None
    xs = sorted(xs)
    k = (len(xs) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


IDLE_FRAME_MS = 1000 / 60   # replaced by the measured idle interval at startup


def frame_stats(frames):
    d = [b - a for a, b in zip(frames, frames[1:])]
    if not d: return {'frames': 0}
    budget = IDLE_FRAME_MS
    return {'frames': len(d), 'median_ms': round(statistics.median(d), 1),
            'p95_ms': round(pct(d, 95), 1), 'max_ms': round(max(d), 1),
            'dropped': sum(1 for x in d if x > budget * 1.5),
            'dropped_pct': round(100 * sum(1 for x in d if x > budget * 1.5) / len(d))}


def call_stats(calls):
    out = {}
    for n, xs in calls.items():
        out[n] = {'n': len(xs), 'total_ms': round(sum(xs), 1), 'median_ms': round(statistics.median(xs), 2),
                  'p95_ms': round(pct(xs, 95), 2), 'max_ms': round(max(xs), 1)}
    return dict(sorted(out.items(), key=lambda kv: -kv[1]['total_ms']))


# Trace event names grouped the way DevTools groups them
PHASE = {
    'Scripting': {'FunctionCall', 'EvaluateScript', 'v8.compile', 'v8.compileModule', 'TimerFire',
                  'FireAnimationFrame', 'EventDispatch', 'V8.GCScavenger', 'MajorGC', 'MinorGC',
                  'V8.GC_SCAVENGER', 'BlinkGC.AtomicPhase', 'v8.run', 'V8.Execute', 'RunMicrotasks',
                  'v8.parseOnBackground', 'ParseHTML', 'HitTest'},
    'Style': {'UpdateLayoutTree', 'RecalculateStyles', 'ScheduleStyleRecalculation'},
    'Layout': {'Layout', 'UpdateLayout', 'InvalidateLayout'},
    'Paint (main thread)': {'Paint', 'PaintImage', 'PrePaint', 'UpdateLayer', 'UpdateLayerTree',
                            'Layerize', 'Commit', 'PaintArtifactCompositor::Update', 'CompositeLayers'},
}


def trace_breakdown(raw):
    """Self time per event name, per thread kind, from a Chrome trace."""
    data = json.loads(raw)
    evs = data['traceEvents'] if isinstance(data, dict) else data
    tname = {}
    for e in evs:
        if e.get('ph') == 'M' and e.get('name') == 'thread_name':
            tname[(e['pid'], e['tid'])] = e['args']['name']
    # renderer pid = the one whose main thread ran FunctionCall
    by_thread = defaultdict(list)
    for e in evs:
        if e.get('ph') == 'X' and 'dur' in e:
            by_thread[(e['pid'], e['tid'])].append(e)
    self_by = defaultdict(lambda: defaultdict(float))
    for key, lst in by_thread.items():
        lst.sort(key=lambda e: (e['ts'], -e['dur']))
        stack = []
        selft = {}
        for i, e in enumerate(lst):
            while stack and lst[stack[-1]]['ts'] + lst[stack[-1]]['dur'] <= e['ts']:
                stack.pop()
            selft[i] = e['dur']
            if stack:
                selft[stack[-1]] -= e['dur']
            stack.append(i)
        name = tname.get(key, '?')
        kind = ('main' if name == 'CrRendererMain' else
                'raster' if 'Raster' in name or 'CompositorTileWorker' in name else
                'compositor' if name == 'Compositor' else
                'gpu' if name in ('CrGpuMain', 'VizCompositorThread', 'Viz') or 'Gpu' in name else None)
        if not kind: continue
        for i, e in enumerate(lst):
            if selft[i] > 0:
                self_by[kind][e['name']] += selft[i] / 1000.0
    phases = defaultdict(float)
    for n, ms in self_by['main'].items():
        for ph, names in PHASE.items():
            if n in names:
                phases[ph] += ms; break
    phases['Raster (tile workers)'] = sum(self_by['raster'].values())
    phases['GPU process'] = sum(self_by['gpu'].values())
    top_main = sorted(self_by['main'].items(), key=lambda kv: -kv[1])[:12]
    return {'phases_ms': {k: round(v, 1) for k, v in phases.items()},
            'top_main_thread_self_ms': [(n, round(ms, 1)) for n, ms in top_main if ms >= 0.5],
            'top_raster_self_ms': [(n, round(ms, 1)) for n, ms in sorted(self_by['raster'].items(), key=lambda kv: -kv[1])[:5]],
            'top_gpu_self_ms': [(n, round(ms, 1)) for n, ms in sorted(self_by['gpu'].items(), key=lambda kv: -kv[1])[:5]]}


def paced(n, dt, fn):
    """Call fn(i) n times, one every dt seconds, like a real input device."""
    t0 = time.perf_counter()
    for i in range(n):
        fn(i)
        wait = t0 + (i + 1) * dt - time.perf_counter()
        if wait > 0: time.sleep(wait)


class Session:
    def __init__(self, pw):
        launch_args = ['--disable-renderer-backgrounding', '--disable-background-timer-throttling',
                       '--disable-backgrounding-occluded-windows',
                       '--disable-features=CalculateNativeWinOcclusion']
        self.browser = pw.chromium.launch(headless=not HEADED, args=launch_args)
        self.page = None

    def open(self):
        if self.page: self.page.context.close()
        ctx = self.browser.new_context(viewport=VIEW, device_scale_factor=DPR)
        self.page = ctx.new_page()
        self.errors = []
        self.page.on('pageerror', lambda e: self.errors.append(str(e)[:200]))
        return self.page

    def load(self, trace=False):
        pg = self.open()
        # stamp the first route drawn: a Canvas 2D stroke, or a WebGL2 draw (v2)
        pg.add_init_script("""(() => {
          const hook = (proto, name) => {
            if (!proto || !proto[name]) return;
            const f = proto[name];
            proto[name] = function (...a) {
              if (!window.__firstStroke) window.__firstStroke = performance.now();
              return f.apply(this, a);
            };
          };
          hook(CanvasRenderingContext2D.prototype, 'stroke');
          hook(window.WebGL2RenderingContext && WebGL2RenderingContext.prototype, 'drawArraysInstanced');
        })()""")
        if trace: self.browser.start_tracing(page=pg, categories=TRACE_CATS)
        pg.goto(URL, wait_until='load')
        pg.wait_for_function('typeof redrawAll === "function"')
        pg.wait_for_timeout(1200)
        tr = self.browser.stop_tracing() if trace else None
        pg.evaluate(INSTRUMENT, WRAP)
        return tr

    def measure(self, fn, trace=True):
        pg = self.page
        pg.wait_for_timeout(300)
        if trace: self.browser.start_tracing(page=pg, categories=TRACE_CATS)
        pg.evaluate(START)
        t0 = time.perf_counter()
        fn(pg)
        wall = time.perf_counter() - t0
        # keep recording briefly so a redraw after the gesture ends (index.html's
        # settle) is counted too
        pg.wait_for_timeout(300)
        r = pg.evaluate(STOP)
        out = {'wall_s': round(wall, 2), 'frame': frame_stats(r['frames']), 'calls': call_stats(r['calls'])}
        if r['tipLat']:
            out['tooltip_latency_ms'] = {'n': len(r['tipLat']), 'median': round(statistics.median(r['tipLat']), 1),
                                         'p95': round(pct(r['tipLat'], 95), 1)}
        if trace:
            out['trace'] = trace_breakdown(self.browser.stop_tracing())
        return out

    def shot(self, name):
        if SHOTS:
            pathlib.Path(SHOTS).mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(pathlib.Path(SHOTS) / f'{name}.png'))


# ---------- scenario helpers (all coordinates are the page's projected units) ----------
VIRGINIA = (-43.0, 27.5)       # lon -78, lat 37.5
KENTUCKY = (-50.0, 27.5)       # lon -85, lat 37.5
ATLANTIC_W, ATLANTIC_E = (-40.0, 22.0), (25.0, 12.0)


def to_screen(pg, xy):
    """Page (viewport) pixel position of data point xy. dataToScreen is relative
    to #map-wrap, which sits below the header, so add the wrapper's offset."""
    return pg.evaluate("""([x,y]) => { const r = mapWrap.getBoundingClientRect();
      const [sx, sy] = dataToScreen(x, y); return [sx + r.left, sy + r.top]; }""", list(xy))


def set_view(pg, xy, k):
    """Center the map on data point xy at zoom k (uses the page's own maths)."""
    pg.evaluate("""([x,y,k]) => {
      const rect = mapWrap.getBoundingClientRect();
      const vx = (rect.width/2 - base.offsetX)/base.scale, vy = (rect.height/2 - base.offsetY)/base.scale;
      currentTransform = d3.zoomIdentity.translate(vx - x*k, vy - y*k).scale(k);
      redrawAll(); updateLabels();
    }""", [xy[0], xy[1], k])
    pg.wait_for_timeout(400)


def zoom_in(pg, to_k=20, dy=-25, hz=60):
    """Trackpad-style wheel zoom from 1x to to_k, centered on Virginia."""
    pg.evaluate('document.getElementById("zoomReset").click()')
    pg.wait_for_timeout(300)
    x, y = to_screen(pg, VIRGINIA)
    pg.mouse.move(x, y)
    n = 0
    while pg.evaluate('currentTransform.k') < to_k and n < 400:
        pg.mouse.wheel(0, dy)
        n += 1
        time.sleep(1 / hz)
    return n


def pan(pg, k, steps=90):
    """Drag across the Atlantic at zoom k (the drag spans the same screen distance at any zoom)."""
    mid = ((ATLANTIC_W[0] + ATLANTIC_E[0]) / 2, (ATLANTIC_W[1] + ATLANTIC_E[1]) / 2)
    set_view(pg, ATLANTIC_W if k > 2 else mid, k)
    sx, sy = 1100, 500
    pg.mouse.move(sx, sy)
    pg.mouse.down()
    paced(steps, 1 / 60, lambda i: pg.mouse.move(sx - 800 * (i + 1) / steps, sy - 150 * (i + 1) / steps))
    pg.mouse.up()


def hover_sweep(pg, k, steps=120):
    """Move the mouse slowly from Kentucky to Virginia and back at zoom k."""
    set_view(pg, ((VIRGINIA[0] + KENTUCKY[0]) / 2, 27.5), k)
    (x1, y1), (x2, y2) = to_screen(pg, KENTUCKY), to_screen(pg, VIRGINIA)
    def mv(i):
        t = i / (steps // 2) if i < steps // 2 else 2 - i / (steps // 2)
        # small vertical wobble so the pointer crosses many routes
        pg.mouse.move(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t + 25 * ((i % 8) - 4) / 4)
    paced(steps, 1 / 60, mv)


def run():
    global IDLE_FRAME_MS
    results = {'url': URL, 'headed': HEADED, 'dpr': DPR, 'viewport': VIEW}
    with sync_playwright() as pw:
        S = Session(pw)
        # control: frame interval of a blank page on this machine, right now
        pg = S.open(); pg.goto('about:blank')
        fr = pg.evaluate("""() => new Promise(res => { const f = []; const t0 = performance.now();
          (function tick(t) { f.push(t); if (t - t0 < 1500) requestAnimationFrame(tick); else res(f); })(t0); })""")
        IDLE_FRAME_MS = statistics.median([b - a for a, b in zip(fr[1:], fr[2:])])
        results['idle_frame_ms'] = round(IDLE_FRAME_MS, 1)
        print(f'idle frame interval on this machine now: {IDLE_FRAME_MS:.1f} ms'
              + ('' if IDLE_FRAME_MS < 18 else '  <-- slower than 60 Hz: on battery? results are not comparable to plugged-in runs'),
              flush=True)

        if not SKIP_MAIN:
            # ---- load ----
            tr = S.load(trace=True)
            pg = S.page
            load = pg.evaluate("""() => {
              const nav = performance.getEntriesByType('navigation')[0];
              const fp = performance.getEntriesByType('paint').find(p => p.name === 'first-paint');
              const fcp = performance.getEntriesByType('paint').find(p => p.name === 'first-contentful-paint');
              return { first_paint_ms: fp && fp.startTime, first_contentful_paint_ms: fcp && fcp.startTime,
                       first_route_drawn_ms: window.__firstStroke, dom_content_loaded_ms: nav.domContentLoadedEventEnd,
                       load_event_ms: nav.loadEventEnd, transfer_kb: Math.round(nav.transferSize/1024) };
            }""")
            # cost of just the data: compile + evaluate the nine data lines in isolation
            # (they live in data.js; legacy.html still carries them inline)
            src = None
            if URL.startswith('http://localhost'):
                f = 'legacy.html' if URL.endswith('legacy.html') else 'data.js'
                src = pathlib.Path(f).read_text(encoding='utf-8') if pathlib.Path(f).exists() else None
            if src:
                data_lines = [l for l in src.splitlines() if re.match(r'const (BASEMAP|ROUTES|CLUSTERS|PLACES|REF_CITIES|VB|SEARCH_INDEX|GRAPH|PERSON_LEGS)\b', l)]
                body = '\n'.join(data_lines) + '\nreturn ROUTES.length;'
                load['data_kb'] = round(len(body.encode()) / 1024)
                load['data_parse_ms'] = pg.evaluate("""(body) => {
                  const ts = [];
                  for (let i = 0; i < 5; i++) { const t0 = performance.now(); new Function(body)(); ts.push(performance.now() - t0); }
                  ts.sort((a,b)=>a-b); return { first: +ts[0].toFixed(1), median: +ts[2].toFixed(1) };
                }""", body)
            load['trace'] = trace_breakdown(tr)
            results['load'] = load
            S.shot('load')

            # ---- zoom ----
            results['zoom_1_to_20'] = S.measure(lambda pg: zoom_in(pg))
            S.shot('zoom20')

            # ---- pan ----
            results['pan_1x'] = S.measure(lambda pg: pan(pg, 1))
            results['pan_8x'] = S.measure(lambda pg: pan(pg, 8))
            S.shot('pan8')

            # ---- hover ----
            results['hover_1x'] = S.measure(lambda pg: hover_sweep(pg, 1))
            results['hover_6x'] = S.measure(lambda pg: hover_sweep(pg, 6))
            S.shot('hover6')

            # ---- setTarget ----
            people = pg.evaluate("""() => {
              const M = GRAPH.james_id;
              // deepest ancestor: the one furthest (most generations) above Margaret
              let deep = null, best = -1;
              for (const id of ancestorSetOf(M)) { const h = hopsToAncestor(M, id); if (h > best && h < Infinity) { best = h; deep = id; } }
              const g = SEARCH_INDEX.find(s => s.name === 'Thomas Godbey Sr.');
              return { margaret: M, deep, deep_name: GRAPH.people[deep].name, deep_generations: best, godbey: g && g.id };
            }""")
            set_view(pg, (-40, 25), 1)
            st = {}
            for label, pid in [('Margaret (default)', people['margaret']),
                               (f"deep ancestor: {people['deep_name']} ({people['deep_generations']} gens up)", people['deep']),
                               ('Thomas Godbey Sr.', people['godbey']), ('back to Margaret', people['margaret'])]:
                # time the call itself, then until the next frame is presented, then until labels settle
                r = pg.evaluate("""(pid) => new Promise(res => {
                  window.__prof.rec = true; window.__prof.calls = {};
                  const t0 = performance.now();
                  setTarget(pid);
                  const t1 = performance.now();
                  requestAnimationFrame(() => requestAnimationFrame(() => {
                    const t2 = performance.now();
                    setTimeout(() => { window.__prof.rec = false;
                      res({ call_ms: t1 - t0, to_next_frame_ms: t2 - t0,
                            labels_ms: (window.__prof.calls.updateLabels || [0]).reduce((a,b)=>a+b,0),
                            recompute_ms: (window.__prof.calls.recomputeClusterVisibility || [0])[0],
                            redraw_ms: (window.__prof.calls.redrawAll || []).reduce((a,b)=>a+b,0),
                            redraws: (window.__prof.calls.redrawAll || []).length }); }, 200);
                  }));
                })""", pid)
                st[label] = {k: round(v, 1) if isinstance(v, float) else v for k, v in r.items()}
                pg.wait_for_timeout(300)
            results['setTarget'] = st
            results['setTarget_trace'] = None

            # ---- time period playback ----
            def playback(pg):
                pg.click('.mode-btn[data-mode="era"]')
                pg.fill('#year-from', '1600'); pg.fill('#year-to', '1625')
                pg.wait_for_timeout(700)
                pg.click('#era-play-btn')
                pg.wait_for_timeout(12000)   # ~60 ticks of the 240-tick sweep
                pg.click('#era-play-btn')
            results['playback_12s'] = S.measure(playback)
            S.shot('playback')

        # ---- ablations: what does each layer cost during zoom and pan? ----
        if ABLATE:
            # Variants are interleaved and repeated so drift (thermals, other
            # windows) hits them all alike; each cell is the median of the reps.
            ABL = {
                'baseline': '() => {}',
                'no basemap': '() => { document.getElementById("basemap-svg").style.display = "none"; }',
                'basemap: far detail only': '() => { BASEMAP.land_near = BASEMAP.land_far; BASEMAP.states_near = BASEMAP.states_far; }',
                'basemap: no state borders': '() => { statesPath.style("display", "none"); }',
                'no place dots': '() => { placesLayer.style("display", "none"); }',
                'no labels': '() => { window.updateLabels = () => {}; document.querySelectorAll(".place-label-html").forEach(d => d.remove()); }',
                'no routes': '() => { window.drawRoutes = () => {}; }',
                'routes only': '() => { document.getElementById("basemap-svg").style.display = "none"; placesLayer.style("display","none"); window.updateLabels = () => {}; document.querySelectorAll(".place-label-html").forEach(d => d.remove()); }',
            }
            if opt('--ablate') == 'stack':
                # cumulative: start from an empty map and add one layer at a time
                HIDE_BASEMAP = 'document.getElementById("basemap-svg").style.display = "none";'
                HIDE_DOTS_LABELS = 'placesLayer.style("display","none"); window.updateLabels = () => {}; document.querySelectorAll(".place-label-html").forEach(d => d.remove());'
                NO_ROUTES = 'window.drawRoutes = () => {}; ctx.clearRect(0, 0, base.width, base.height);'
                ABL = {
                    'nothing (empty map)': f'() => {{ {HIDE_BASEMAP} {HIDE_DOTS_LABELS} {NO_ROUTES} }}',
                    '+ basemap': f'() => {{ {HIDE_DOTS_LABELS} {NO_ROUTES} }}',
                    '+ dots and labels': f'() => {{ {NO_ROUTES} }}',
                    '+ routes (= full page)': '() => {}',
                }
            reps = int(opt('--reps', 3))
            raw = defaultdict(lambda: defaultdict(list))
            for rep in range(reps):
                for name, js in ABL.items():
                    S.load()
                    S.page.evaluate(js)
                    for scen, fn in [('pan_8x', lambda pg: pan(pg, 8, steps=60)), ('zoom', lambda pg: zoom_in(pg, to_k=12, dy=-40))]:
                        m = S.measure(fn)
                        gpu = dict(m['trace']['top_gpu_self_ms'])
                        raw[name][scen].append((m['frame']['median_ms'], m['frame']['p95_ms'], m['frame']['dropped_pct'],
                                                m['wall_s'], gpu.get('RasterDecoderImpl::DoRasterCHROMIUM::Deserializing', 0)))
                print(f'  ablation rep {rep + 1}/{reps} done', flush=True)
            abl = {}
            for name, scens in raw.items():
                abl[name] = {}
                for scen, rows in scens.items():
                    cols = list(zip(*rows))
                    abl[name][scen] = {'median_ms': statistics.median(cols[0]), 'p95_ms': statistics.median(cols[1]),
                                       'dropped_pct': statistics.median(cols[2]),
                                       'gpu_deserialize_ms_per_s': round(statistics.median([d / w for d, w in zip(cols[4], cols[3])])),
                                       'runs': rows}
            results['ablations'] = abl

        results['page_errors'] = S.errors
        S.browser.close()
    return results


def report(R):
    p = print
    p(f"\nProfile of {R['url']}  ({'headed' if R['headed'] else 'headless'}, dpr {R['dpr']}, {R['viewport']['width']}x{R['viewport']['height']}, "
      f"idle frame {R.get('idle_frame_ms', '?')} ms)\n")
    if 'load' not in R:
        return report_ablations(R)
    L = R['load']
    p('LOAD')
    p(f"  first paint {L['first_paint_ms']:.0f} ms | first route drawn {L['first_route_drawn_ms']:.0f} ms | "
      f"DOMContentLoaded {L['dom_content_loaded_ms']:.0f} ms | load {L['load_event_ms']:.0f} ms")
    if 'data_parse_ms' in L:
        p(f"  data {L['data_kb']} KB: compile+evaluate {L['data_parse_ms']['first']} ms (best of 5), median {L['data_parse_ms']['median']} ms")
    p(f"  phases: {L['trace']['phases_ms']}")
    p(f"  top main-thread: {L['trace']['top_main_thread_self_ms'][:6]}")
    p('\nFRAMES              frames  median   p95    max   dropped')
    for key in ['zoom_1_to_20', 'pan_1x', 'pan_8x', 'hover_1x', 'hover_6x', 'playback_12s']:
        f = R[key]['frame']
        if not f.get('frames'): p(f'  {key:18} (no frames)'); continue
        p(f"  {key:18} {f['frames']:5}  {f['median_ms']:6} {f['p95_ms']:6} {f['max_ms']:6}   {f['dropped']} ({f['dropped_pct']}%)")
    for key in ['zoom_1_to_20', 'pan_1x', 'pan_8x', 'hover_1x', 'hover_6x', 'playback_12s']:
        s = R[key]
        p(f"\n{key.upper()}  ({s['wall_s']} s)")
        if 'tooltip_latency_ms' in s: p(f"  mousemove -> tooltip change: {s['tooltip_latency_ms']}")
        for n, c in list(s['calls'].items())[:7]:
            p(f"  {n:26} n={c['n']:4}  total {c['total_ms']:7} ms  median {c['median_ms']:6}  p95 {c['p95_ms']:6}  max {c['max_ms']}")
        t = s.get('trace')
        if t:
            p(f"  phases (ms): {t['phases_ms']}")
            p(f"  top main-thread self time: {t['top_main_thread_self_ms'][:8]}")
            if t['top_raster_self_ms']: p(f"  top raster: {t['top_raster_self_ms'][:3]}")
    p('\nSETTARGET')
    for k, v in R['setTarget'].items(): p(f'  {k:52} {v}')
    report_ablations(R)


def report_ablations(R):
    p = print
    if 'ablations' in R:
        p('\nABLATIONS  frame median / p95 ms / dropped%  | GPU deserialize ms per second of gesture')
        p(f"  {'':28} {'pan at 8x':>34}   {'zoom 1-12x':>34}")
        for n, a in R['ablations'].items():
            cells = []
            for scen in ['pan_8x', 'zoom']:
                c = a[scen]
                cells.append(f"{c['median_ms']:>6} / {c['p95_ms']:>6} / {c['dropped_pct']:>3}% | {c['gpu_deserialize_ms_per_s']:>5}")
            p(f"  {n:28} {cells[0]:>34}   {cells[1]:>34}")
    if R['page_errors']: p(f"\nPAGE ERRORS: {R['page_errors']}")


if __name__ == '__main__':
    R = run()
    if JSON_OUT:   # save before printing, so a report bug never loses a long run
        pathlib.Path(JSON_OUT).write_text(json.dumps(R, indent=1))
    report(R)
