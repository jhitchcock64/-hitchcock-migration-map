"""
Stage 9: military service. Reads ../military/itineraries.py (hand-authored
from pension files, service records and family histories), routes each leg
over the same historical network as the likely routes (stage 8), and writes
military_prepared.json -> MILITARY in data.js:

  { pid: [ {war, unit, summary, sources: [...],
            stops: [{l: label, x, y, d: date, c: conf, n?: note}],
            legs:  [{i: index of the stop it ends at, c: conf, p: [[x, y], ...], via?: 'corridor names'}] } ] }

conf is the stop's: 'record', 'unit', 'family' or 'conjecture' (see
itineraries.py). A leg takes the confidence of the stop it ends at. Legs
into a stop marked gap aren't drawn. A leg whose stop lists network nodes
(via) follows them; otherwise the router infers the path for the year, and
a leg the router can't place (short, or off the network) is a straight line.

Needs stage 8's inputs (it imports build_corridor_routes for the network).
"""
import json, re, sys, pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / 'military'))
import build_corridor_routes as bcr
from itineraries import SERVICE

OUT = HERE / 'military_prepared.json'
CONF = {'record', 'unit', 'family', 'conjecture'}
# network modes a leg may NOT use, by how it travelled (itineraries.py 'by')
SKIP = {'land': {'rail', 'highway', 'interstate', 'sea', 'river', 'canal'},
        'water': {'rail', 'highway', 'interstate'}, 'sea': {'rail', 'highway', 'interstate'}, 'rail': set()}


def year_of(date, default=None):
    m = re.search(r'1[5-9]\d\d', date or '')
    if m: return int(m.group(0))
    if default is None: raise SystemExit(f'no year in date {date!r}')
    return default     # 'date unknown': the year of the stop before


def r2(p): return [round(p[0], 4), round(p[1], 4)]


def leg_path(a, b, stop):
    """a, b: stops. -> (list of [x, y], corridor names)."""
    x1, y1 = bcr.to_xy(a['lon'], a['lat']); x2, y2 = bcr.to_xy(b['lon'], b['lat'])
    lead = [[x1, y1]] + [bcr.to_xy(lon, lat) for lat, lon in stop.get('way') or []]   # fixed waypoints first
    x1, y1 = lead[-1]
    year = stop['_year']
    if stop.get('via'):
        steps = []
        for u, w in zip(stop['via'], stop['via'][1:]): steps += bcr.node_path(u, w, year)
        entry, exit_ = stop['via'][0], stop['via'][-1]
        v = {'e': steps, 'h': [[x1, y1], bcr.to_xy(*bcr.NODE_LL[entry])], 't': [bcr.to_xy(*bcr.NODE_LL[exit_]), [x2, y2]]}
    else:
        a_ll, b_ll = bcr.to_ll(x1, y1), bcr.to_ll(x2, y2)
        r = bcr._route(a_ll, b_ll, year, SKIP[stop['by']], bcr.CONNECT_KM, bcr.CONNECT_KM)
        v = None
        if r and r != 'guard':
            steps, entry, exit_ = r
            v = {'e': steps,
                 'h': [[x1, y1], bcr.to_xy(*bcr.NODE_LL[entry])] if bcr.km(a_ll, bcr.NODE_LL[entry]) > 1 else [],
                 't': [bcr.to_xy(*bcr.NODE_LL[exit_]), [x2, y2]] if bcr.km(bcr.NODE_LL[exit_], b_ll) > 1 else []}
    if not v: return [list(p) for p in lead] + [[x2, y2]], ''
    pts, names = [list(p) for p in lead[:-1]] + [list(p) for p in (v['h'] or [lead[-1]])], []
    for s in v['e']:
        e = bcr.EDGES[abs(s) - 1]
        c = e['coords'] if s > 0 else e['coords'][::-1]
        xy = [bcr.to_xy(*p) for p in c]
        pts += xy if not pts else xy[1:] if pts[-1] == xy[0] else xy
        if e['name'] != 'Local road' and (not names or names[-1] != e['name']): names.append(e['name'])
    pts += v['t'][1:] if v['t'] else [[x2, y2]]
    pts = [tuple(p) for p in pts]
    pts = bcr.dp(pts, 0.004) if len(pts) > 2 else pts
    rail = [n for n in names if re.search(r'\brail', n, re.I)]
    names = [n for n in names if n not in rail] + (['railroads'] if rail else [])
    return [list(p) for p in pts], ' > '.join(names)


def main():
    out, log = {}, []
    for s in SERVICE:
        stops, legs, yr = [], [], None
        for st in s['stops']:                        # an undated stop takes the year of the one before
            yr = year_of(st['date'], yr); st['_year'] = yr
        for i, st in enumerate(s['stops']):
            if st['conf'] not in CONF: raise SystemExit(f"{s['name']}: bad conf {st['conf']!r}")
            x, y = bcr.to_xy(st['lon'], st['lat'])
            d = {'l': st['label'], 'x': round(x, 4), 'y': round(y, 4), 'd': st['date'], 'c': st['conf']}
            if st['note']: d['n'] = st['note']
            stops.append(d)
            if i and not st['gap']:
                p, via = leg_path(s['stops'][i - 1], st, st)
                leg = {'i': i, 'c': st['conf'], 'p': [r2(q) for q in p]}
                if via: leg['via'] = via
                legs.append(leg)
                log.append(f"  {s['name']:26} {s['stops'][i-1]['label'][:28]:28} > {st['label'][:34]:34} "
                           f"{st['conf']:10} {via or '(direct)'}")
        out.setdefault(s['pid'], []).append({'war': s['war'], 'unit': s['unit'], 'summary': s['summary'],
                                             'sources': s['sources'], 'stops': stops, 'legs': legs})
    OUT.write_text(json.dumps(out, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')
    n_routes = sum(1 for v in out.values() for e in v if e['stops'])
    print(f'{len(SERVICE)} entries for {len(out)} people ({n_routes} with routes, '
          f'{len(SERVICE) - n_routes} notes only); {OUT.stat().st_size // 1024} KB')
    print('\n'.join(log))


if __name__ == '__main__':
    main()
