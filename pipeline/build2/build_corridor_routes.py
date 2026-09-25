"""
Stage 8: "likely routes". For each overland move, find the path a traveller
of that year would most plausibly have taken -- period roads, navigable
rivers, canals and coastal sea lanes, then railroads, then highways and
Interstates -- or leave the move as a direct line when nothing fits.

Input:  routes_prepared.json, person_legs.json (this folder),
        ../corridors/network.json (hand-authored roads, rivers, sea lanes),
        ../corridors/modern_network.json.gz (railroads, highways)
Output: corridors_prepared.json -> CORRIDORS in data.js:
  { edges:  [{name, mode, c: [[x, y], ...]}],             (projected units)
    routes: {route index: {e: [+-(edge index + 1)], h: [[x, y], ...], t: [[x, y], ...], a?: 1, n?: note}},
    legs:   {"x1,y1,x2,y2,year" (coordinates x100, rounded): same} }
  "edges" here are the stretches of network the routes use, merged so that
  each is one run shared by the same routes (so one band on the map). e lists
  them in travel order (negative = walked backwards); h and t are the short
  overland links from the documented place to the network and back.

This is inference, not evidence: records rarely say how a family travelled.
The page shows these paths only when the viewer asks for likely routes.

Cost model (per km; the cheapest path wins):
  overland to or from the network        2.5   (at most CONNECT_KM each end)
  period road                            1.0   (x the corridor's cost_factor)
  sea lane, canal                        0.5
  river, downstream                      0.35
  river, upstream (from upstream_from)   0.5
  railroad                               0.3   (0.45 after 1945)
  highway                                0.7   (0.45 after 1945)
  Interstate                             0.3
  plus a fixed cost to board a boat (BOARD_COST) or a train (RAIL_BOARD_COST),
  so a short hop doesn't beat the road. Each network is usable only in its
  years (network.py; railroads from the year each line opened to 1955;
  highways from 1920, Interstates from 1960 -- see build_network.py).
Moves listed in network.py's FORCED follow the nodes given there (the family's
own research, e.g. Lochry's expedition) and carry a note (n) for the tooltip.
A move is routed only if the path beats going direct (2.5/km), is no more
than MAX_DETOUR x the direct distance (+50 km; river trips wind), and at
least 40% of it is on the network. Moves under MIN_KM keep their direct
lines. Ocean crossings are routed too (overland to a port, a sea lane, a port
to the destination); where that fails they keep the pipeline's ocean path. A move to or from a place known only as a state,
colony or country ("Virginia"; see REGIONS) is routed from where the map
already puts that place, and marked approximate (a: 1) so the page can say so.
"""
import json, math, heapq, pathlib, gzip
from collections import defaultdict, Counter

HERE = pathlib.Path(__file__).resolve().parent
CORR = HERE.parent / 'corridors'
ROUTES = json.load(open(HERE / 'routes_prepared.json', encoding='utf-8'))
LEGS = json.load(open(HERE / 'person_legs.json', encoding='utf-8'))
OUT = HERE / 'corridors_prepared.json'

CONNECT_COST, CONNECT_KM, BOARD_COST, RAIL_BOARD_COST = 2.5, 160, 80, 40
REGION_CONNECT_KM = 400   # a place known only as a state or country sits at its centre
MIN_KM, MAX_DETOUR, DETOUR_SLACK_KM, MIN_ON_NETWORK = 80, 2.3, 50, 0.4
TRANSFER_KM = 25          # a town on the hand-made network links to a station or highway this close
MIN_COST_PER_KM = 0.15    # the cheapest mode (trade-wind sea lane, 0.5 x 0.3): A*'s estimate of
                          # the rest of the trip; must not exceed any real cost, or A* can miss the best path
WATER, RAIL = {'river', 'sea', 'canal'}, {'rail'}


def to_ll(x, y):
    lon = x - 35
    if lon < -180: lon += 360
    elif lon >= 180: lon -= 360
    return lon, 65 - y


def to_xy(lon, lat):
    x = lon + 35
    if x >= 180: x -= 360
    return [round(x, 3), round(65 - lat, 3)]


def km(a, b):
    r = math.pi / 180
    h = (math.sin((b[1] - a[1]) * r / 2) ** 2 +
         math.cos(a[1] * r) * math.cos(b[1] * r) * math.sin((b[0] - a[0]) * r / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(min(1, h)))


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


# ---------------------------------------------------------------- the network
NET = json.load(open(CORR / 'network.json', encoding='utf-8'))
MODERN = json.loads(gzip.decompress((CORR / 'modern_network.json.gz').read_bytes()))
NODE_LL = {k: (v[2], v[1]) for k, v in NET['nodes'].items()}
NODE_LL.update({k: tuple(v) for k, v in MODERN['nodes'].items()})
EDGES = NET['edges'] + MODERN['edges']
for e in MODERN['edges']:
    if e['mode'] == 'rail' and 'rail' not in e['name'].lower(): e['name'] += ' (railroad)'

GRID = defaultdict(list)                    # 1-degree cells -> node ids
for n, (x, y) in NODE_LL.items(): GRID[(math.floor(x), math.floor(y))].append(n)


def near(p, radius_km, ports_only=False):
    """[(node, km)] within radius of p (lon, lat); ports_only: skip the '~'
    waypoints at sea, which a traveller can't walk to."""
    dy = radius_km / 111 + 1; dx = radius_km / (111 * max(0.2, math.cos(math.radians(p[1])))) + 1
    out = []
    for gx in range(math.floor(p[0] - dx), math.floor(p[0] + dx) + 1):
        for gy in range(math.floor(p[1] - dy), math.floor(p[1] + dy) + 1):
            for n in GRID.get((gx, gy), ()):
                if ports_only and n.startswith('~'): continue
                d = km(p, NODE_LL[n])
                if d <= radius_km: out.append((n, d))
    return out


# towns on the hand-made network connect to the nearest station and highway
for n, v in NET['nodes'].items():
    if v[0].startswith('~'): continue
    best = {}
    for m, d in near(NODE_LL[n], TRANSFER_KM):
        kind = 'r' if m.startswith('r') else 'h' if m.startswith('h') else None
        if kind and (kind not in best or d < best[kind][1]): best[kind] = (m, d)
    for m, d in best.values():
        EDGES.append(dict(a=n, b=m, name='Local road', mode='transfer', years=[0, 3000], km=round(d, 2),
                          coords=[list(NODE_LL[n]), list(NODE_LL[m])]))

ARCS = defaultdict(list)          # node -> [(neighbour, edge index, sign)]
for i, e in enumerate(EDGES):
    ARCS[e['a']].append((e['b'], i, 1)); ARCS[e['b']].append((e['a'], i, -1))


def cost_per_km(e, sign, year, private_ok=False):
    """None if the edge can't be used that year in that direction."""
    if not (e['years'][0] <= year <= e['years'][1]): return None
    if 'closed' in e and e['closed'][0] <= year <= e['closed'][1]: return None     # e.g. occupied New York
    if e.get('private') and not private_ok: return None
    m = e['mode']
    if m == 'river':
        if sign == 1: c = 0.35
        elif year >= e.get('upstream_from', 9999): c = 0.5
        else: return None
    elif m in ('sea', 'canal'): c = 0.5
    elif m == 'road': c = 1.0
    elif m == 'rail': c = 0.3 if year <= 1945 else 0.45
    elif m == 'highway': c = 0.7 if year < 1945 else 0.45
    elif m == 'interstate': c = 0.3
    else: c = 1.0                                  # transfer
    return c * e.get('cost_factor', 1)


def klass(mode):
    return 1 if mode in WATER else 2 if mode in RAIL else 0


def route(a, b, year, ra=CONNECT_KM, rb=CONNECT_KM):
    """a, b: (lon, lat). Returns (signed edge list, entry node, exit node) or None.
    If the cheapest path fails the guards because it goes round by sea (Bern ->
    Le Havre down the Rhine and round by the Channel), try again over land."""
    r = _route(a, b, year, set(), ra, rb)
    if r == 'guard': r = _route(a, b, year, {'sea'}, ra, rb)
    return r if r != 'guard' else None


def _route(a, b, year, skip, ra, rb):
    """A* over (node, travelling by land / water / rail) states; skip: modes not
    to use. Returns (steps, entry, exit), None, or 'guard' when the best path
    breaks the detour or on-network guards."""
    direct = km(a, b)
    if direct < MIN_KM: return None
    exits = {n: d * CONNECT_COST for n, d in near(b, abs(rb), ports_only=rb > 0)}
    if not exits: return None
    h = lambda n: km(NODE_LL[n], b) * MIN_COST_PER_KM
    dist, prev, heap = {}, {}, []
    for n, d in near(a, abs(ra), ports_only=ra > 0):
        s = (n, 0)
        if d * CONNECT_COST < dist.get(s, 1e18):
            dist[s] = d * CONNECT_COST; heapq.heappush(heap, (dist[s] + h(n), dist[s], n, 0))
    best, best_cost = None, direct * CONNECT_COST          # must beat going direct
    while heap:
        f, d, u, cls = heapq.heappop(heap)
        if f >= best_cost: break
        if d > dist[(u, cls)]: continue
        if u in exits and d + exits[u] < best_cost: best, best_cost = (u, cls), d + exits[u]
        for v, i, sign in ARCS[u]:
            e = EDGES[i]
            if e['mode'] in skip: continue
            c = cost_per_km(e, sign, year)
            if c is None: continue
            k = klass(e['mode']) if e['mode'] != 'transfer' else cls
            nd = d + e['km'] * c
            if k and k != cls: nd += BOARD_COST if k == 1 else RAIL_BOARD_COST
            if nd < dist.get((v, k), 1e18):
                dist[(v, k)] = nd; prev[(v, k)] = (u, cls, i, sign)
                heapq.heappush(heap, (nd + h(v), nd, v, k))
    if best is None: return None
    steps, st = [], best
    while st in prev:
        u, cls, i, sign = prev[st]; steps.append(sign * (i + 1)); st = (u, cls)
    steps.reverse()
    if not steps: return None
    entry, exit_ = st[0], best[0]
    on_net = sum(EDGES[abs(s) - 1]['km'] for s in steps)
    total = on_net + km(a, NODE_LL[entry]) + km(NODE_LL[exit_], b)
    if total > direct * MAX_DETOUR + DETOUR_SLACK_KM or on_net < MIN_ON_NETWORK * total: return 'guard'
    return steps, entry, exit_


def ocean(x1, x2):
    # the same test as rebuild_all_data.py's is_ocean_crossing: one end in the
    # Americas (west of 25 W), the other not
    return (to_ll(x1, 0)[0] < -25) != (to_ll(x2, 0)[0] < -25)


# Places recorded only as a state, colony or country: no point to route from
REGIONS = {
    'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut', 'Delaware',
    'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky',
    'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi', 'Missouri',
    'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey', 'New Mexico', 'New York',
    'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island',
    'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington',
    'West Virginia', 'Wisconsin', 'Wyoming', 'United States', 'USA', 'America', 'Canada', 'Mexico',
    'England', 'Scotland', 'Wales', 'Ireland', 'Northern Ireland', 'Great Britain', 'United Kingdom',
    'Germany', 'Switzerland', 'Sweden', 'France', 'Netherlands', 'Holland', 'Prussia',
}


def precise(label):
    # "Surry, Virginia" or "Hadley" is a place; a bare "Virginia" is only the state or colony
    return bool(label) and label.strip() not in REGIONS


def node_path(u, v, year):
    """Cheapest edge path between two network nodes (private corridors allowed)."""
    dist, prev, heap = {u: 0}, {}, [(0, u)]
    while heap:
        d, n = heapq.heappop(heap)
        if n == v: break
        if d > dist[n]: continue
        for m, i, sign in ARCS[n]:
            c = cost_per_km(EDGES[i], sign, year, private_ok=True)
            if c is None: continue
            nd = d + EDGES[i]['km'] * c
            if nd < dist.get(m, 1e18): dist[m] = nd; prev[m] = (n, i, sign); heapq.heappush(heap, (nd, m))
    if v not in dist: raise SystemExit(f'FORCED route: no path from {u} to {v} in {year}')
    steps, n = [], v
    while n != u:
        n, i, sign = prev[n]; steps.append(sign * (i + 1))
    return steps[::-1]


FORCED = {tuple(f['match']): f for f in NET.get('forced', [])}


def forced(frm, to, year, x1, y1, x2, y2):
    f = FORCED.get((frm, to, round(year)))
    if not f: return None
    if not f.get('via'):
        v = _via(x1, y1, x2, y2, year)
        return dict(v, n=f['note']) if v else None
    steps = []
    for u, w in zip(f['via'], f['via'][1:]): steps += node_path(u, w, year)
    a, b, entry, exit_ = to_ll(x1, y1), to_ll(x2, y2), f['via'][0], f['via'][-1]
    return {'e': steps, 'n': f['note'],
            'h': [[x1, y1], to_xy(*NODE_LL[entry])] if km(a, NODE_LL[entry]) > 1 else [],
            't': [to_xy(*NODE_LL[exit_]), [x2, y2]] if km(NODE_LL[exit_], b) > 1 else []}


_cache = {}


def via(x1, y1, x2, y2, year, frm, to):
    f = forced(frm, to, year, x1, y1, x2, y2)
    if f: return f
    ra = CONNECT_KM if precise(frm) else REGION_CONNECT_KM
    rb = CONNECT_KM if precise(to) else REGION_CONNECT_KM
    # someone recorded as born "at sea" can join a sea lane where they were (negative radius)
    if 'at sea' in (frm or '').lower(): ra = -ra
    if 'at sea' in (to or '').lower(): rb = -rb
    v = _via(x1, y1, x2, y2, year, ra, rb)
    if v and not (precise(frm) and precise(to)): v = dict(v, a=1)
    return v


def _via(x1, y1, x2, y2, year, ra=CONNECT_KM, rb=CONNECT_KM):
    key = (round(x1, 3), round(y1, 3), round(x2, 3), round(y2, 3), year, ra, rb)
    if key not in _cache:
        a, b = to_ll(x1, y1), to_ll(x2, y2)
        r = route(a, b, year, ra, rb)
        if not r: _cache[key] = None
        else:
            steps, entry, exit_ = r
            _cache[key] = {'e': steps,
                           'h': [[x1, y1], to_xy(*NODE_LL[entry])] if km(a, NODE_LL[entry]) > 1 else [],
                           't': [to_xy(*NODE_LL[exit_]), [x2, y2]] if km(NODE_LL[exit_], b) > 1 else []}
    return _cache[key]


def leg_key(l):
    return ','.join(str(round(v * 100)) for v in (l['x1'], l['y1'], l['x2'], l['y2'])) + ',' + str(l['year'])


def ends(e, sign):
    return (e['a'], e['b']) if sign > 0 else (e['b'], e['a'])


def merge_runs(paths, sig_of):
    """Merge the used network edges into runs: maximal chains of edges of one
    mode, used by exactly the same routes, joined end to end with no other
    path entering or leaving between them. -> (runs, edge -> (run, sign))."""
    used = set(abs(s) - 1 for p in paths for s in p)
    deg = Counter()
    for i in used: deg[EDGES[i]['a']] += 1; deg[EDGES[i]['b']] += 1
    breaks = {n for n, d in deg.items() if d != 2}
    for p in paths:                                  # every path starts and ends on a run boundary
        breaks.add(ends(EDGES[abs(p[0]) - 1], p[0])[0]); breaks.add(ends(EDGES[abs(p[-1]) - 1], p[-1])[1])
    at = defaultdict(list)
    for i in used: at[EDGES[i]['a']].append(i); at[EDGES[i]['b']].append(i)
    for n, es in at.items():
        if len(es) == 2:
            e1, e2 = EDGES[es[0]], EDGES[es[1]]
            if sig_of[es[0]] != sig_of[es[1]] or e1['mode'] != e2['mode']: breaks.add(n)
    seen, runs, where = set(), [], {}
    order = sorted(used)
    def walk(start_edge, start_node):
        seq, n, i = [], start_node, start_edge
        while True:
            e = EDGES[i]; sign = 1 if e['a'] == n else -1
            seq.append((i, sign)); seen.add(i)
            n = e['b'] if sign == 1 else e['a']
            if n in breaks: break
            nxt = [j for j in at[n] if j != i and j not in seen]
            if not nxt: break
            i = nxt[0]
        return seq
    for i in order:                                  # runs starting at a boundary
        if i in seen: continue
        e = EDGES[i]
        if e['a'] in breaks: seq = walk(i, e['a'])
        elif e['b'] in breaks: seq = walk(i, e['b'])
        else: continue
        runs.append(seq)
    for i in order:                                  # closed loops, if any
        if i not in seen: runs.append(walk(i, EDGES[i]['a']))
    for r, seq in enumerate(runs):
        for i, sign in seq: where[i] = (r, sign)
    return runs, where


def main():
    routes, legs = {}, {}
    for i, r in enumerate(ROUTES):
        c = r['curve']
        if c['mode'] == 'bow': (x1, y1), (x2, y2) = (c['x1'], c['y1']), (c['x2'], c['y2'])
        else: (x1, y1), (x2, y2) = c['coords'][0], c['coords'][-1]
        v = via(x1, y1, x2, y2, r['mean_year'], r['from'], r['to'])
        if v: routes[str(i)] = v
    for pid, ls in LEGS.items():
        for l in ls:
            if l.get('year') is None: continue
            v = via(l['x1'], l['y1'], l['x2'], l['y2'], l['year'], l['from'], l['to'])
            if v: legs[leg_key(l)] = v

    # merge the network edges they use into runs, each one band on the map
    sig = defaultdict(set)
    for rid, v in routes.items():
        for s in v['e']: sig[abs(s) - 1].add(rid)
    sig_of = defaultdict(frozenset, {i: frozenset(s) for i, s in sig.items()})
    all_paths = [v['e'] for v in routes.values()] + [v['e'] for v in legs.values()]
    runs, where = merge_runs(all_paths, sig_of)

    def remap(steps):
        out, k = [], 0
        while k < len(steps):
            i, sign = abs(steps[k]) - 1, (1 if steps[k] > 0 else -1)
            r, rs = where[i]; d = sign * rs
            n = len(runs[r])
            seq = [(abs(s) - 1) for s in steps[k:k + n]]
            want = [j for j, _ in runs[r]] if d == 1 else [j for j, _ in runs[r]][::-1]
            assert seq == want, 'a path covers part of a run'
            out.append(d * (r + 1)); k += n
        return out
    out_routes = {k: dict(v, e=remap(v['e'])) for k, v in routes.items()}
    out_legs = {k: dict(v, e=remap(v['e'])) for k, v in legs.items()}
    edges = []
    for seq in runs:
        coords, names = [], Counter()
        for i, sign in seq:
            e = EDGES[i]; c = e['coords'] if sign == 1 else e['coords'][::-1]
            coords += c if not coords else c[1:]
            names[e['name']] += e['km']
        mode = EDGES[seq[0][0]]['mode']
        pts = coords if mode in ('road', 'sea', 'canal') else dp([tuple(p) for p in coords], 0.003)
        edges.append({'name': names.most_common(1)[0][0], 'mode': mode, 'c': [to_xy(*p) for p in pts]})
    out = {'edges': edges, 'routes': out_routes, 'legs': out_legs}
    OUT.write_text(json.dumps(out, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')

    used = Counter()
    for v in routes.values():
        for n in dict.fromkeys(EDGES[abs(s) - 1]['name'] for s in v['e']): used[n] += 1
    modes = Counter()
    for v in routes.values():
        for m in dict.fromkeys(EDGES[abs(s) - 1]['mode'] for s in v['e']): modes[m] += 1
    print(f'routes routed over the network: {len(routes)} of {len(ROUTES)}; person legs: {len(legs)}; '
          f'{len(edges)} runs, {OUT.stat().st_size // 1024} KB')
    print('routes using each kind of network: ' + ', '.join(f'{m} {n}' for m, n in modes.most_common()))
    print()
    print('routes per corridor (top 40):')
    for k, n in used.most_common(40): print(f'  {n:4}  {k}')
    print()
    print('routed moves (year, from > to | corridors taken):')
    for i, v in sorted(routes.items(), key=lambda kv: (ROUTES[int(kv[0])]['mean_year'], int(kv[0]))):
        r, seq = ROUTES[int(i)], []
        for st in v['e']:
            n = EDGES[abs(st) - 1]['name']
            if n != 'Local road' and (not seq or seq[-1] != n): seq.append(n)
        if len(seq) > 8: seq = seq[:4] + ['...'] + seq[-3:]
        print(f"  {r['mean_year']:5.0f}  {r['from']} > {r['to']}  |  {' > '.join(seq)}")


if __name__ == '__main__':
    main()
