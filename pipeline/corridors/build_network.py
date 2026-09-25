"""
Turns network.py (the hand-authored corridors) into network.json: one edge
per consecutive pair of nodes, each with its drawn geometry in lon/lat.

Roads, canals and sea lanes: a smooth curve (centripetal Catmull-Rom)
through the corridor's nodes. Rivers: the real river line from Natural Earth 1:10m
(pipeline/basemap/cache/, see build_basemap.py for the download), cut
between consecutive river towns (or, with geometry='spline', a curve through
the listed points, for rivers Natural Earth doesn't cover end to end).

Railroads and highways (modern.py) go to modern_network.json.gz: railroads
from Jeremy Atack's historical GIS (usable from the year each line opened
until RAIL_LAST_YEAR), US and Canadian highways from Natural Earth (from
HIGHWAY_FIRST_YEAR; Interstates from INTERSTATE_FIRST_YEAR).

Both outputs are committed, so the pipeline itself needs no map data; rerun
this only after editing network.py or modern.py (needs pipeline/basemap/cache/):
    python pipeline/corridors/build_network.py
"""
import json, math, heapq, pathlib, sys, gzip
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from network import NODES, CORRIDORS, RIVER, CLOSED

CACHE = HERE.parent / 'basemap' / 'cache'
OUT = HERE / 'network.json'
MODERN_OUT = HERE / 'modern_network.json.gz'
RAIL_LAST_YEAR = 1955          # after the war, long moves went by car
HIGHWAY_FIRST_YEAR = 1920      # auto trails from the 1910s; US numbered highways 1926
INTERSTATE_FIRST_YEAR = 1960   # most of the system opened 1956-1975


def km(a, b):      # (lon, lat) points
    r = math.pi / 180
    h = (math.sin((b[1] - a[1]) * r / 2) ** 2 +
         math.cos(a[1] * r) * math.cos(b[1] * r) * math.sin((b[0] - a[0]) * r / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(min(1, h)))


def length(pts):
    return sum(km(a, b) for a, b in zip(pts, pts[1:]))


def catmull_rom(pts, per_seg=10):
    """Centripetal Catmull-Rom through pts; returns one list of samples per segment."""
    if len(pts) < 2: return []
    P = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        def tj(ti, a, b):
            return ti + max(1e-9, math.hypot(b[0] - a[0], b[1] - a[1])) ** 0.5
        t0 = 0; t1 = tj(t0, p0, p1); t2 = tj(t1, p1, p2); t3 = tj(t2, p2, p3)
        seg = []
        for k in range(per_seg + 1):
            t = t1 + (t2 - t1) * k / per_seg
            def lerp(a, b, ta, tb):
                if tb - ta < 1e-12: return a
                return ((tb - t) / (tb - ta) * a[0] + (t - ta) / (tb - ta) * b[0],
                        (tb - t) / (tb - ta) * a[1] + (t - ta) / (tb - ta) * b[1])
            A1 = lerp(p0, p1, t0, t1); A2 = lerp(p1, p2, t1, t2); A3 = lerp(p2, p3, t2, t3)
            B1 = lerp(A1, A2, t0, t2); B2 = lerp(A2, A3, t1, t3)
            seg.append(lerp(B1, B2, t1, t2))
        seg[0], seg[-1] = p1, p2
        out.append(seg)
    return out


def dp(pts, tol):
    if len(pts) < 3: return pts
    keep = [False] * len(pts); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        ax, ay = pts[i]; bx, by = pts[j]; dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
        best, bi = -1, -1
        for k in range(i + 1, j):
            px, py = pts[k]
            t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
            d = math.hypot(px - ax - t * dx, py - ay - t * dy)
            if d > best: best, bi = d, k
        if best > tol:
            keep[bi] = True; stack += [(i, bi), (bi, j)]
    return [p for p, k in zip(pts, keep) if k]


def river_graph(name):
    """All Natural Earth lines named `name`, as a vertex graph (gaps under ~2 km bridged)."""
    parts = []
    for f in ('ne_10m_rivers_lake_centerlines.geojson', 'ne_10m_rivers_north_america.geojson'):
        for ft in json.load(open(CACHE / f, encoding='utf-8'))['features']:
            p = ft['properties']
            if (p.get('name') or p.get('name_en')) != name: continue
            g = ft['geometry']
            parts += g['coordinates'] if g['type'] == 'MultiLineString' else [g['coordinates']]
    key = lambda p: (round(p[0], 5), round(p[1], 5))
    adj = defaultdict(dict)
    for part in parts:
        for a, b in zip(part, part[1:]):
            ka, kb = key(a), key(b); d = km(ka, kb)
            adj[ka][kb] = d; adj[kb][ka] = d
    ends = [k for k in adj if len(adj[k]) == 1]
    for i, a in enumerate(ends):
        for b in ends[i + 1:]:
            d = km(a, b)
            if d < 2.0: adj[a][b] = d; adj[b][a] = d
    return adj


def nearest(adj, p):
    best = min(adj, key=lambda k: km(k, p))
    return best, km(best, p)


def shortest(adj, s, t):
    dist = {s: 0}; prev = {}; h = [(0, s)]
    while h:
        d, u = heapq.heappop(h)
        if u == t: break
        if d > dist[u]: continue
        for v, w in adj[u].items():
            if d + w < dist.get(v, 1e18):
                dist[v] = d + w; prev[v] = u; heapq.heappush(h, (d + w, v))
    if t not in dist: return None
    path = [t]
    while path[-1] != s: path.append(prev[path[-1]])
    return path[::-1]


def main():
    ll = {k: (v[2], v[1]) for k, v in NODES.items()}          # id -> (lon, lat)
    edges = {}                                                 # (a, b) -> edge
    problems = []
    for c in CORRIDORS:
        path = c['path']
        for n in path:
            if n not in NODES: raise SystemExit(f'{c["name"]}: unknown node {n}')
        if c['mode'] == RIVER and c.get('geometry') != 'spline':
            adj = river_graph(c['river'])
            if not adj: raise SystemExit(f'no Natural Earth line named {c["river"]}')
            geoms = []
            for a, b in zip(path, path[1:]):
                (sa, da), (sb, db) = nearest(adj, ll[a]), nearest(adj, ll[b])
                for n, d in ((a, da), (b, db)):
                    if d > 12: problems.append(f'{c["name"]}: {n} is {d:.0f} km from the river line')
                vs = shortest(adj, sa, sb)
                if vs is None:
                    problems.append(f'{c["name"]}: {a} -> {b} not connected along the river; straight line used')
                    vs = [sa, sb]
                geoms.append([ll[a]] + dp(vs, 0.012) + [ll[b]])
        else:
            geoms = catmull_rom([ll[n] for n in path], per_seg=10)
        for (a, b), g in zip(zip(path, path[1:]), geoms):
            yrs = c.get('seg_years', {}).get((a, b), c['years'])
            k = (a, b) if (b, a) not in edges else (b, a)
            if k in edges:          # the same stretch in two corridors: one edge, both names
                e = edges[k]
                if c['name'] not in e['name'].split(' / '): e['name'] += ' / ' + c['name']
                e['years'] = [min(e['years'][0], yrs[0]), max(e['years'][1], yrs[1])]
                continue
            e = dict(a=a, b=b, name=c['name'], mode=c['mode'], years=list(yrs),
                     coords=[[round(x, 4), round(y, 4)] for x, y in g])
            if c['mode'] == RIVER: e['upstream_from'] = c.get('upstream_from', yrs[0])
            if c.get('cost_factor'): e['cost_factor'] = c['cost_factor']
            if c.get('frontier'): e['frontier'] = True
            for n in (a, b):
                if n in CLOSED: e['closed'] = list(CLOSED[n])
            e['km'] = round(length(e['coords']), 1)
            edges[k] = e
    out = dict(nodes={k: [v[0], v[1], v[2]] for k, v in NODES.items()}, edges=list(edges.values()))
    OUT.write_text(json.dumps(out, separators=(',', ':'), ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    by = defaultdict(float)
    for e in out['edges']: by[e['mode']] += e['km']
    print(f'{len(out["edges"])} edges, ' + ', '.join(f'{m} {v:,.0f} km' for m, v in by.items()) +
          f' -> {OUT.name} ({OUT.stat().st_size // 1024} KB)')
    for p in problems: print('  WARNING', p)
    build_modern()


def build_modern():
    import modern
    nodes, edges = {}, []
    for pieces in (modern.rail_pieces(CACHE), modern.road_pieces(CACHE)):
        n, es = modern.finish(pieces)
        nodes.update(n); edges += es
    for e in edges:
        if e['mode'] == 'rail': e['years'] = [e.pop('year'), RAIL_LAST_YEAR]
        elif e['mode'] == 'interstate': e.pop('year'); e['years'] = [INTERSTATE_FIRST_YEAR, 2100]
        else: e.pop('year'); e['years'] = [HIGHWAY_FIRST_YEAR, 2100]
    edges.sort(key=lambda e: (e['a'], e['b'], e['mode'], e['coords'][0]))
    out = dict(nodes={k: [round(v[0], 4), round(v[1], 4)] for k, v in sorted(nodes.items())}, edges=edges)
    raw = json.dumps(out, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    MODERN_OUT.write_bytes(gzip.compress(raw, mtime=0))
    by = defaultdict(float)
    for e in edges: by[e['mode']] += e['km']
    print(f'{len(edges)} railroad and highway edges, ' + ', '.join(f'{m} {v:,.0f} km' for m, v in by.items()) +
          f' -> {MODERN_OUT.name} ({MODERN_OUT.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    main()
