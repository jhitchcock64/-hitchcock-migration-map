"""
Stage 8: "likely routes". For each overland move, find the path a traveller
of that year would most plausibly have taken over the historical network
(pipeline/corridors/network.json: period roads, navigable rivers, coastal
sea lanes), or leave the move as a direct line when the network doesn't fit.

Input:  routes_prepared.json, person_legs.json (this folder),
        ../corridors/network.json
Output: corridors_prepared.json -> CORRIDORS in data.js:
  { edges:  [{name, mode, c: [[x, y], ...]}],             (projected units)
    routes: {route index: {e: [+-(edge index + 1)], h: [[x, y], ...], t: [[x, y], ...]}},
    legs:   {"x1,y1,x2,y2,year" (coordinates x100, rounded): same} }
  e lists the network edges in travel order (negative = edge walked from b to a);
  h and t are the short overland connections from the documented place to the
  network and from the network to the documented place.

This is inference, not evidence: records rarely say how a family travelled.
The page shows these paths only when the viewer asks for likely routes.

Cost model (per km; the cheapest path wins):
  overland to or from the network   2.5   (at most CONNECT_KM each end)
  road                              1.0
  sea lane, canal                   0.5
  river, downstream                 0.35
  river, upstream (steamboat era)   0.6   (only from the river's upstream_from year)
  (an edge's cost_factor multiplies these: the Tennessee's Muscle Shoals)
  getting onto a boat (river, canal or sea) from land   BOARD_COST (in km-equivalents),
  the time and money to find or build a boat, so a short river hop doesn't beat the road
A move is routed only if the network path beats going direct (2.5/km), is
no more than 2.3x the direct distance (+50 km; river trips wind), and at
least 40% of it is on the network. Railroads: from 1850, moves over 400 km
aren't routed along eastern roads (at most 30% of the path); after 1860 only
moves made mostly by river (70%), starting and ending within 60 km of it,
are routed. Frontier trails (the California Trail) are exempt. Moves under MIN_KM, ocean crossings,
moves outside the network's years and moves to or from a place known only
as a state, colony or country ("Virginia"; see REGIONS) keep their direct lines.
"""
import json, math, heapq, pathlib

HERE = pathlib.Path(__file__).resolve().parent
NET = json.load(open(HERE.parent / 'corridors' / 'network.json', encoding='utf-8'))
ROUTES = json.load(open(HERE / 'routes_prepared.json', encoding='utf-8'))
LEGS = json.load(open(HERE / 'person_legs.json', encoding='utf-8'))
OUT = HERE / 'corridors_prepared.json'

CONNECT_COST, CONNECT_KM, BOARD_COST = 2.5, 160, 80
COST = {'road': 1.0, 'sea': 0.5, 'canal': 0.5, 'river_down': 0.35, 'river_up': 0.6}
MIN_KM, MAX_DETOUR, DETOUR_SLACK_KM, MIN_ON_NETWORK = 80, 2.3, 50, 0.4
RAIL_ERA, MIN_RIVER_SHARE_RAIL_ERA, RAIL_CONNECT_KM = 1860, 0.7, 60
LONG_ROAD_END, LONG_ROAD_KM, MAX_ROAD_SHARE_LONG = 1850, 400, 0.3


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


NODE_LL = {k: (v[2], v[1]) for k, v in NET['nodes'].items()}
EDGES = NET['edges']
# directed arcs: node -> [(neighbour, edge index, sign, mode key, edge)]
ARCS = {}
for i, e in enumerate(EDGES):
    for u, v, sign in ((e['a'], e['b'], 1), (e['b'], e['a'], -1)):
        if e['mode'] == 'river': key = 'river_down' if sign == 1 else 'river_up'
        else: key = e['mode']
        ARCS.setdefault(u, []).append((v, i, sign, key, e))


def usable(e, key, year):
    if not (e['years'][0] <= year <= e['years'][1]): return False
    if key == 'river_up' and year < e.get('upstream_from', e['years'][0]): return False
    return True


def route(a, b, year):
    """a, b: (lon, lat). Returns (edge list, entry node, exit node) or None."""
    direct = km(a, b)
    if direct < MIN_KM: return None
    # states are (node, on water?): boarding a boat from land costs BOARD_COST
    dist, prev, heap = {}, {}, []
    for n, p in NODE_LL.items():
        d = km(a, p)
        if d <= CONNECT_KM:
            dist[(n, False)] = d * CONNECT_COST; heapq.heappush(heap, (dist[(n, False)], n, False))
    if not dist: return None
    while heap:
        d, u, wet = heapq.heappop(heap)
        if d > dist[(u, wet)]: continue
        for v, i, sign, key, e in ARCS.get(u, ()):
            if not usable(e, key, year): continue
            water = e['mode'] != 'road'
            nd = d + e['km'] * COST[key] * e.get('cost_factor', 1) + (BOARD_COST if water and not wet else 0)
            if nd < dist.get((v, water), 1e18):
                dist[(v, water)] = nd; prev[(v, water)] = (u, wet, i, sign); heapq.heappush(heap, (nd, v, water))
    best, best_cost = None, 1e18
    for (n, wet), d in dist.items():
        dd = km(NODE_LL[n], b)
        if dd <= CONNECT_KM and d + dd * CONNECT_COST < best_cost:
            best, best_cost = (n, wet), d + dd * CONNECT_COST
    if best is None or best_cost >= direct * CONNECT_COST: return None
    steps, st = [], best
    while st in prev:
        u, wet, i, sign = prev[st]; steps.append(sign * (i + 1)); st = (u, wet)
    steps.reverse()
    n, best = st[0], best[0]
    if not steps: return None
    entry = n
    on_net = sum(EDGES[abs(s) - 1]['km'] for s in steps)
    total = on_net + km(a, NODE_LL[entry]) + km(NODE_LL[best], b)
    if total > direct * MAX_DETOUR + DETOUR_SLACK_KM or on_net < MIN_ON_NETWORK * total: return None
    def share(test): return sum(EDGES[abs(s) - 1]['km'] for s in steps if test(EDGES[abs(s) - 1])) / total
    if year >= LONG_ROAD_END and direct > LONG_ROAD_KM:
        if share(lambda e: e['mode'] == 'road' and not e.get('frontier')) > MAX_ROAD_SHARE_LONG: return None
    if year > RAIL_ERA:
        if share(lambda e: e['mode'] == 'river' or e.get('frontier')) < MIN_RIVER_SHARE_RAIL_ERA: return None
        if max(km(a, NODE_LL[entry]), km(NODE_LL[best], b)) > RAIL_CONNECT_KM: return None
    return steps, entry, best


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


def via(x1, y1, x2, y2, year, frm, to):
    if not (precise(frm) and precise(to)): return None
    a, b = to_ll(x1, y1), to_ll(x2, y2)
    r = route(a, b, year)
    if not r: return None
    steps, entry, exit_ = r
    h = [[x1, y1], to_xy(*NODE_LL[entry])] if km(a, NODE_LL[entry]) > 1 else []
    t = [to_xy(*NODE_LL[exit_]), [x2, y2]] if km(NODE_LL[exit_], b) > 1 else []
    return {'e': steps, 'h': h, 't': t}


def leg_key(l):
    return ','.join(str(round(v * 100)) for v in (l['x1'], l['y1'], l['x2'], l['y2'])) + ',' + str(l['year'])


def main():
    routes, legs = {}, {}
    for i, r in enumerate(ROUTES):
        c = r['curve']
        if c['mode'] == 'bow': (x1, y1), (x2, y2) = (c['x1'], c['y1']), (c['x2'], c['y2'])
        else:
            # waypointed: ocean crossings (never touched) and the older single-waypoint
            # corridors of rebuild_all_data.py (e.g. VA -> KY through the Cumberland Gap)
            (x1, y1), (x2, y2) = c['coords'][0], c['coords'][-1]
            if ocean(x1, x2): continue
        v = via(x1, y1, x2, y2, r['mean_year'], r['from'], r['to'])
        if v: routes[str(i)] = v
    for pid, ls in LEGS.items():
        for l in ls:
            if l.get('ocean') or l.get('year') is None: continue
            v = via(l['x1'], l['y1'], l['x2'], l['y2'], l['year'], l['from'], l['to'])
            if v: legs[leg_key(l)] = v
    edges = [{'name': e['name'], 'mode': e['mode'], 'c': [to_xy(*p) for p in e['coords']]} for e in EDGES]
    out = {'edges': edges, 'routes': routes, 'legs': legs}
    OUT.write_text(json.dumps(out, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')
    used = {}
    for v in routes.values():
        for s in v['e']: used[EDGES[abs(s) - 1]['name']] = used.get(EDGES[abs(s) - 1]['name'], 0) + 1
    print(f'routes routed over the network: {len(routes)} of {len(ROUTES)}; person legs: {len(legs)}')
    print()
    print('routes per corridor:')
    for k, n in sorted(used.items(), key=lambda x: -x[1]): print(f'  {n:4}  {k}')
    # every routed move, for review (pipeline/logs/build_corridor_routes.log)
    print()
    print('routed moves (year, from > to | corridors taken):')
    for i, v in sorted(routes.items(), key=lambda kv: (ROUTES[int(kv[0])]['mean_year'], int(kv[0]))):
        r, seq = ROUTES[int(i)], []
        for st in v['e']:
            n = EDGES[abs(st) - 1]['name']
            if not seq or seq[-1] != n: seq.append(n)
        print(f"  {r['mean_year']:5.0f}  {r['from']} > {r['to']}  |  {' > '.join(seq)}")


if __name__ == '__main__':
    main()
