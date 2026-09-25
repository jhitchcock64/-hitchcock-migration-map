"""
Railroads and highways for the historical network (used by build_network.py).

Railroads: Jeremy Atack, "Historical Geographic Information Systems (GIS)
database of U.S. Railroads", 1826-1911 (Vanderbilt University; file
RR1826-1911Modified103123.zip). Every segment carries InOpBy, the year it was
in operation. Albers equal-area metres -> lon/lat. Well noded already:
segments meeting within 200 m are joined.

Highways: Natural Earth 1:10m roads (public domain; ne_10m_roads.zip), US and
Canada, levels Interstate / Federal (US highways) / State. Natural Earth
doesn't split roads where they meet, so this nodes them: lines are split
where they cross, and a road ending within SNAP_KM of another road is joined
to it.

Both are then contracted: chains of segments between junctions become one
edge (years: the latest along the chain; name: the longest piece's), and
simplified for drawing.
"""
import math
from collections import defaultdict, Counter
from shapefile import read_zip, AlbersInverse

RAIL_ZIP, RAIL_STEM = 'RR1826-1911Modified103123.zip', 'RR1826-1911Modified103123'
ROADS_ZIP, ROADS_STEM = 'ne_10m_roads.zip', 'ne_10m_roads'
RAIL_NODE_M = 200
SNAP_KM = 1.5
SIMPLIFY_DEG = 0.004


def km(a, b):
    r = math.pi / 180
    h = (math.sin((b[1] - a[1]) * r / 2) ** 2 +
         math.cos(a[1] * r) * math.cos(b[1] * r) * math.sin((b[0] - a[0]) * r / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(min(1, h)))


def length(pts):
    return sum(km(a, b) for a, b in zip(pts, pts[1:]))


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


def contract(pieces):
    """pieces: [(node_a, node_b, coords a->b, props)] -> same, with degree-2 chains of
    equal 'mode' merged. props: mode, year (first usable), name."""
    adj = defaultdict(list)
    for i, (a, b, c, p) in enumerate(pieces):
        if a == b: continue
        adj[a].append(i); adj[b].append(i)
    used, out = set(), []

    def through(n, came):   # continue a chain through degree-2 node n (same mode)
        if len(adj[n]) != 2: return None
        j = adj[n][0] if adj[n][1] == came else adj[n][1]
        if j in used or j == came or pieces[j][3]['mode'] != pieces[came][3]['mode']: return None
        return j

    for i, (a, b, c, p) in enumerate(pieces):
        if i in used or a == b: continue
        used.add(i)
        chain = [(i, 1)]
        # extend forward from b, then backward from a
        for end, forward in ((b, True), (a, False)):
            n, last = end, i
            while True:
                j = through(n, last)
                if j is None: break
                used.add(j)
                ja, jb = pieces[j][0], pieces[j][1]
                sign = 1 if ja == n else -1
                if forward: chain.append((j, sign)); n = jb if sign == 1 else ja
                else: chain.insert(0, (j, -sign)); n = ja if sign == 1 else jb
                last = j
        coords, names, year = [], Counter(), 0
        for j, s in chain:
            cj = pieces[j][2] if s == 1 else pieces[j][2][::-1]
            coords += cj if not coords else cj[1:]
            names[pieces[j][3]['name']] += length(pieces[j][2])
            year = max(year, pieces[j][3]['year'])
        first, last = chain[0], chain[-1]
        na = pieces[first[0]][0] if first[1] == 1 else pieces[first[0]][1]
        nb = pieces[last[0]][1] if last[1] == 1 else pieces[last[0]][0]
        out.append((na, nb, coords, dict(p, year=year, name=names.most_common(1)[0][0])))
    return out


def rail_pieces(cache):
    recs, shapes = read_zip(cache / RAIL_ZIP, RAIL_STEM)
    inv = AlbersInverse(37.5, -96, 29.5, 45.5)
    key = lambda p: 'r%d_%d' % (round(p[0] / RAIL_NODE_M), round(p[1] / RAIL_NODE_M))
    pieces = []
    for r, s in zip(recs, shapes):
        year = r.get('InOpBy') or 0
        if not year: continue
        for part in s:
            if len(part) < 2: continue
            pieces.append((key(part[0]), key(part[-1]), [inv(*p) for p in part],
                           dict(mode='rail', year=int(year), name=(r.get('RRname') or 'Railroad').strip() or 'Railroad')))
    return pieces


def road_name(r):
    n = (r.get('name') or '').strip()
    if r['level'] == 'Interstate': return f'I-{n}' if n else 'Interstate'
    if r['level'] == 'Federal': return (f'US {n}' if r['sov_a3'] == 'USA' else f'Highway {n}') if n else 'Highway'
    return f'Highway {n}' if n else 'State highway'


def road_pieces(cache):
    recs, shapes = read_zip(cache / ROADS_ZIP, ROADS_STEM)
    lines = []                        # (coords, props)
    for r, s in zip(recs, shapes):
        if r['sov_a3'] not in ('USA', 'CAN') or r['featurecla'] != 'Road': continue
        if r['level'] not in ('Federal', 'State', 'Interstate'): continue
        mode = 'interstate' if r['level'] == 'Interstate' else 'highway'
        for part in s:
            if len(part) >= 2: lines.append(([tuple(p) for p in part], dict(mode=mode, year=0, name=road_name(r))))
    # ---- noding: split points per line (as positions along the segment list)
    CELL = 0.25
    grid = defaultdict(list)             # cell -> [(line, seg index)]
    for li, (c, _) in enumerate(lines):
        for si in range(len(c) - 1):
            (x1, y1), (x2, y2) = c[si], c[si + 1]
            for gx in range(int(math.floor(min(x1, x2) / CELL)), int(math.floor(max(x1, x2) / CELL)) + 1):
                for gy in range(int(math.floor(min(y1, y2) / CELL)), int(math.floor(max(y1, y2) / CELL)) + 1):
                    grid[(gx, gy)].append((li, si))
    splits = defaultdict(set)           # line -> {(seg index, t)}
    joins = []                          # extra short links (point a, point b)
    seen = set()
    for cell, segs in grid.items():
        for i in range(len(segs)):
            li, si = segs[i]
            (ax, ay), (bx, by) = lines[li][0][si], lines[li][0][si + 1]
            for j in range(i + 1, len(segs)):
                lj, sj = segs[j]
                if lj == li: continue
                k = (li, si, lj, sj)
                if k in seen: continue
                seen.add(k)
                (cx, cy), (dx, dy) = lines[lj][0][sj], lines[lj][0][sj + 1]
                den = (bx - ax) * (dy - cy) - (by - ay) * (dx - cx)
                if den == 0: continue
                t = ((cx - ax) * (dy - cy) - (cy - ay) * (dx - cx)) / den
                u = ((cx - ax) * (by - ay) - (cy - ay) * (bx - ax)) / den
                if 0 <= t <= 1 and 0 <= u <= 1:
                    splits[li].add((si, t)); splits[lj].add((sj, u))
    # road ends that stop short of another road: join them to the nearest point on it
    for li, (c, _) in enumerate(lines):
        for end in (c[0], c[-1]):
            gx, gy = int(math.floor(end[0] / CELL)), int(math.floor(end[1] / CELL))
            best = None
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    for lj, sj in grid.get((gx + ox, gy + oy), ()):
                        if lj == li: continue
                        (cx, cy), (dx, dy) = lines[lj][0][sj], lines[lj][0][sj + 1]
                        vx, vy = dx - cx, dy - cy; L = vx * vx + vy * vy
                        t = 0 if L == 0 else max(0, min(1, ((end[0] - cx) * vx + (end[1] - cy) * vy) / L))
                        p = (cx + t * vx, cy + t * vy)
                        d = km(end, p)
                        if d < SNAP_KM and (best is None or d < best[0]): best = (d, lj, sj, t, p)
            if best and best[0] > 0.01:
                _, lj, sj, t, p = best
                splits[lj].add((sj, t)); joins.append((end, p))
    key = lambda p: 'h%d_%d' % (round(p[0] * 1e4), round(p[1] * 1e4))
    pieces = []
    for li, (c, props) in enumerate(lines):
        pts = defaultdict(list)
        for si, t in splits[li]: pts[si].append(t)
        cur = [c[0]]
        for si in range(len(c) - 1):
            (ax, ay), (bx, by) = c[si], c[si + 1]
            for t in sorted(pts.get(si, ())):
                p = (ax + t * (bx - ax), ay + t * (by - ay))
                if p != cur[-1]: cur.append(p)
                if len(cur) >= 2: pieces.append((key(cur[0]), key(cur[-1]), cur, props))
                cur = [p]
            if c[si + 1] != cur[-1]: cur.append(c[si + 1])
        if len(cur) >= 2: pieces.append((key(cur[0]), key(cur[-1]), cur, props))
    for a, b in joins:
        pieces.append((key(a), key(b), [a, b], dict(mode='highway', year=0, name='Highway')))
    return pieces


def finish(pieces, keep=lambda p: True):
    """contract, drop what's cut off from the main network, simplify -> (nodes, edges)."""
    edges = contract(pieces)
    par = {}
    def f(x):
        while par.setdefault(x, x) != x: par[x] = par[par[x]]; x = par[x]
        return x
    for a, b, c, p in edges: par[f(a)] = f(b)
    size = Counter()
    for a, b, c, p in edges: size[f(a)] += length(c)
    main = {r for r, s in size.items() if s > 150}          # keep every network over 150 km
    nodes, out = {}, []
    for a, b, c, p in edges:
        if f(a) not in main or not keep(p): continue
        c = dp(c, SIMPLIFY_DEG)
        nodes[a] = c[0]; nodes[b] = c[-1]
        out.append(dict(a=a, b=b, coords=[[round(x, 4), round(y, 4)] for x, y in c], km=round(length(c), 2), **p))
    return nodes, out
