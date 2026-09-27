"""
Stage 10: notable events. Reads ../notable/events.py (hand-authored) and adds
an arrival for every documented ocean crossing into the Americas in the
migrations (person_legs.json), then writes notable_prepared.json -> NOTABLE
in data.js:

  { sex: {pid: 'M' | 'F'},                         (every ancestor's, so the page can say "grandfather")
    events: [{p: [pids], d: date, y: year, t: text, l: place, x, y2: projected point,
              k: 'event' | 'arrival' | 'story', s: source, sh?: ship,
              r?: route index, f?: fraction along it}] }

An event with `on` (a birth at sea) names the route of that person's move in
that year and how far along it; the page pins it on the route as drawn.

A hand-written arrival (kind 'arrival') replaces the automatic one for the same
people within two years, so a landing with its ship and story isn't pinned twice.
Needs stages 1-7 (indi.json, person_legs.json).
"""
import json, sys, pathlib
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'notable'))
from events import EVENTS, NO_ARRIVAL

LEGS = json.load(open(HERE / 'person_legs.json', encoding='utf-8'))
ROUTES = json.load(open(HERE / 'routes_prepared.json', encoding='utf-8'))
GRAPH = json.load(open(HERE / 'person_graph.json', encoding='utf-8'))['people']
INDI = json.load(open(HERE.parent / 'project' / 'indi.json', encoding='utf-8'))
OUT = HERE / 'notable_prepared.json'


def to_xy(lon, lat):
    x = lon + 35
    x = (x + 180) % 360 - 180
    return round(x, 4), round(65 - lat, 4)


def americas(x): return x - 35 < -25          # projected x back to longitude


def route_of(pid, year):
    """The ROUTES index of pid's move in that year (matched by its end points)."""
    leg = next((l for l in LEGS.get(pid, []) if l['year'] == year), None)
    if not leg: raise SystemExit(f'no {year} move for {pid}')
    near = lambda p, x, y: abs(p[0] - x) < 0.02 and abs(p[1] - y) < 0.02
    for i, r in enumerate(ROUTES):
        c = r['curve']
        a, b = (c['coords'][0], c['coords'][-1]) if c['mode'] == 'path' else ((c['x1'], c['y1']), (c['x2'], c['y2']))
        if near(a, leg['x1'], leg['y1']) and near(b, leg['x2'], leg['y2']): return i
    raise SystemExit(f'no route for the {year} move of {pid}')


def point_along(c, f):
    if c['mode'] == 'bow':
        return [(1 - f) ** 2 * c['x1'] + 2 * (1 - f) * f * c['cx'] + f * f * c['x2'],
                (1 - f) ** 2 * c['y1'] + 2 * (1 - f) * f * c['cy'] + f * f * c['y2']]
    pts = c['coords']
    seg = [((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 for a, b in zip(pts, pts[1:])]
    goal = f * sum(seg)
    for (a, b), s in zip(zip(pts, pts[1:]), seg):
        if goal <= s: t = goal / s if s else 0; return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]
        goal -= s
    return list(pts[-1])


def main():
    out, missing = [], []
    for e in EVENTS:
        for pid in e['pids']:
            if pid not in GRAPH: missing.append((pid, e['text'][:50]))
        x, y = to_xy(e['lon'], e['lat'])
        d = {'p': e['pids'], 'd': e['date'], 'y': e['year'], 't': e['text'], 'l': e['place'], 'x': x, 'y2': y,
             'k': e['kind'], 's': e['source']}
        if e['ship']: d['sh'] = e['ship']
        if e.get('on'):
            pid, year, f = e['on']
            d['r'], d['f'] = route_of(pid, year), f
            d['x'], d['y2'] = [round(v, 4) for v in point_along(ROUTES[d['r']]['curve'], f)]
        out.append(d)
    if missing: raise SystemExit(f'events name people not in the graph: {missing}')

    # hand-written arrivals claim (person, year +-2)
    claimed = {(pid, y) for e in EVENTS if e['kind'] == 'arrival' for pid in e['pids'] for y in range(e['year'] - 2, e['year'] + 3)}
    groups = defaultdict(list)
    for pid, legs in LEGS.items():
        if pid not in GRAPH or pid in NO_ARRIVAL: continue
        for l in legs:
            if not l.get('ocean') or l.get('year') is None: continue
            if not americas(l['x2']) or americas(l['x1']): continue
            if (pid, l['year']) in claimed: continue
            groups[(l['to'], l['year'], l['from'], l['x2'], l['y2'])].append(pid)
    auto = 0
    for (to, year, frm, x2, y2), pids in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        names = [GRAPH[p]['name'] for p in pids]
        who = names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1]
        out.append({'p': pids, 'd': str(year), 'y': year, 't': f'{who} arrive{"s" if len(pids) == 1 else ""} at {to} from {frm}.',
                    'l': to, 'x': round(x2, 4), 'y2': round(y2, 4), 'k': 'arrival', 's': 'the migration records in the tree'})
        auto += 1
    out.sort(key=lambda d: (d['y'], d['l']))
    # everyone's, not only these events' people: the page also names relationships for
    # the military layer's battles ("Margaret's 6th great-grandfather")
    sex = {p: INDI[p]['sex'] for p in GRAPH if INDI.get(p, {}).get('sex')}
    OUT.write_text(json.dumps({'sex': sex, 'events': out}, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')
    print(f'{len(EVENTS)} hand-written events, {auto} automatic arrivals; {len(out)} in all; {OUT.stat().st_size // 1024} KB')


if __name__ == '__main__':
    main()
