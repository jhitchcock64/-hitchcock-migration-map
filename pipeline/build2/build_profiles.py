"""
Stage 11: a profile for everyone on the map (the people in GRAPH), for the
page's profile panel. Reads the GEDCOM (for burials, the tree's own events,
notes and attached records), stage 1-2's indi.json, fam.json and events.json
(birth, death, residences and marriages, with the hand corrections), GRAPH
(who is in the line), and ../profiles/stories.py (hand-written life stories).
Writes profiles_prepared.json:

  { sources: [record title, ...],
    people: { pid: {
      b: [date, place], d: [date, place], bu: burial place,
      f: [{sp: {i?: pid if on the map, n: name, y: 'years', lv?: 1}, m: [date, place],
           k: [{i?: pid if in the line, n, y: 'years', bp, dp, lv?: 1, r?: 'step' | 'adopted' ...}]}],
      sb?: [siblings, as k: the birth family's other children],
      t: [[year, 'date', kind, place, note?, url?], ...]   (kind: born, lived, married, event
                                                            text, military, died, buried)
      nt: [research note, ...], r: [source index, ...], st?: {title, text: [...]} } } }

lv marks a living child or spouse who isn't on the map; write_data_js.py
hides those (and the living on the map) with privacy.py. The page writes the
generated summary itself from these facts.
"""
import html, json, os, re, sys, pathlib
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = HERE.parent / 'project'
sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(HERE.parent / 'profiles'))
import geocoder
from privacy import LIVING_BORN_FROM
from stories import STORIES
from privacy import living_ids

# portraits: pipeline/profiles/photos.json (pid -> {file in photos/, source, original}); web-sized
# JPEGs in the repo's photos/ folder. Never for the living (they would be public).
PHOTOS = json.load(open(HERE.parent / 'profiles' / 'photos.json', encoding='utf-8'))
PHOTO_DIR = HERE.parent.parent / 'photos'

GED = os.environ.get('GEDCOM') or sys.exit('Set GEDCOM=/path/to/export.ged (run_pipeline.sh does)')
INDI = json.load(open(PROJECT / 'indi.json', encoding='utf-8'))
FAM = json.load(open(PROJECT / 'fam.json', encoding='utf-8'))
EVENTS = json.load(open(PROJECT / 'events.json', encoding='utf-8'))
GRAPH = json.load(open(HERE / 'person_graph.json', encoding='utf-8'))
OUT = HERE / 'profiles_prepared.json'


TALLY = re.compile(r'\b(males?|females?)\b', re.I)


def year(s):
    m = re.search(r'(1[3-9]\d\d|20[0-2]\d)', s or '')
    return int(m.group(1)) if m else None


def clean_name(n): return re.sub(r'\s+', ' ', (n or '').replace('/', '')).strip()


def place(raw):
    """A short place label: the geocoder's for a town or county, else the tree's text tidied."""
    if not raw: return ''
    try:
        g = geocoder.normalize_and_geocode(raw)
    except Exception:
        g = None
    mc = lambda s: re.sub(r'\b(Mc)([a-z])', lambda m: m.group(1) + m.group(2).upper(), s)
    if g and g[3] in ('town', 'county'): return mc(g[0])
    parts = [p.strip() for p in raw.split(',') if p.strip()]
    parts = [p for p in parts if p.lower() not in ('usa', 'united states', 'united states of america')]
    if len(parts) > 3: parts = [parts[0]] + parts[-2:]        # the town, then the region and country
    return mc(', '.join(parts)) if parts else raw.strip()


def date_text(s):
    if not s: return ''
    s = re.sub(r'\bAbt\.?\s*', 'about ', s.strip()); s = re.sub(r'\bBef\.?\s*', 'before ', s); s = re.sub(r'\bAft\.?\s*', 'after ', s)
    return s.replace('  ', ' ')


# ---------------------------------------------------------------- the GEDCOM's own details
recs, cur = {}, None
for line in open(GED, encoding='utf-8-sig', errors='replace'):
    line = line.rstrip('\n\r')
    if line.startswith('0 '):
        m = re.match(r'0 (@[^@]+@) (\w+)', line); cur = m.group(1) if m else None
        if cur: recs[cur] = []
    elif cur:
        m = re.match(r'\d+ (CONC|CONT) ?(.*)', line)
        if m and recs[cur]:                                 # a long value continues on the next lines
            recs[cur][-1] += (' ' if m.group(1) == 'CONT' else '') + html.unescape(m.group(2))
        else: recs[cur].append(html.unescape(line))
titles = {k: next((l[7:] for l in v if l.startswith('1 TITL ')), None) for k, v in recs.items() if k.startswith('@S')}


def blocks(pid, tags):
    """Level-1 facts with the given tags: [{'t', 'v', DATE, PLAC, TYPE, NOTE}]."""
    out, b = [], None
    for l in recs.get(pid, []):
        m = re.match(r'1 (\w+)\s?(.*)', l)
        if m:
            b = {'t': m.group(1), 'v': m.group(2)} if m.group(1) in tags else None
            if b: out.append(b)
        elif b:
            m = re.match(r'2 (DATE|PLAC|TYPE|NOTE) (.*)', l)
            if m and m.group(1) not in b: b[m.group(1)] = m.group(2)
    return out


def sources_of(pid):
    return sorted({titles.get(s) for l in recs.get(pid, []) for s in re.findall(r'SOUR (@S\d+@)', l)} - {None, 'Ancestry Family Trees'})


def living_other(pid, parent_years):
    """A child or spouse not on the map: living by the same rule as privacy.py."""
    i = INDI.get(pid, {})
    if i.get('deat_date') or i.get('deat_plac') or blocks(pid, ('DEAT', 'BURI')): return False
    by = year(i.get('birt_date'))
    if by: return by >= LIVING_BORN_FROM
    return any(y and y >= LIVING_BORN_FROM - 40 for y in parent_years)


def years(pid):
    i = INDI.get(pid, {})
    a, b = year(i.get('birt_date')), year(i.get('deat_date'))
    abt = lambda s: ('before ' if re.search(r'\bbef', s or '', re.I) else 'after ' if re.search(r'\baft', s or '', re.I)
                     else 'about ' if re.search(r'\b(abt|about|est)', s or '', re.I) else '')
    if a and b: return f'{abt(i.get("birt_date"))}{a}–{abt(i.get("deat_date"))}{b}'
    if a: return f'{abt(i.get("birt_date"))}{a}'.strip()
    if b: return f'died {b}'
    return ''


# ---------------------------------------------------------------- one profile
P = GRAPH['people']
src_index, src_list = {}, []


def profile(pid):
    i, ev = INDI.get(pid, {}), EVENTS.get(pid, {}).get('events', [])
    first = lambda t: next((e for e in ev if e['type'] == t), None)
    b, d = first('BIRT'), first('DEAT')
    bu = next((x for x in blocks(pid, ('BURI',)) if x.get('PLAC')), None)
    pr = {'b': [date_text(b and b['date']), place(b and b['plac'])] if b else ['', ''],
          'd': [date_text(d and d['date']), place(d and d['plac'])] if d else ['', '']}
    if bu: pr['bu'] = place(bu['PLAC'])
    by = year(i.get('birt_date'))
    # families
    fams = []
    for fid in i.get('fams', []):
        f = FAM.get(fid, {})
        sp = next((x for x in (f.get('husb'), f.get('wife')) if x and x != pid), None)
        fam = {}
        if sp:
            s = {'n': clean_name(INDI.get(sp, {}).get('name')), 'y': years(sp)}
            if sp in P: s['i'] = sp
            elif living_other(sp, [by]): s['lv'] = 1
            fam['sp'] = s
        marr = next((x for x in blocks(fid, ('MARR',))), None)
        if marr: fam['m'] = [date_text(marr.get('DATE')), place(marr.get('PLAC'))]
        kids = []
        for k in f.get('chil', []):
            ki = INDI.get(k, {})
            r = ki.get('famc_rel', {}).get(fid)       # this family is a step/adopted/guardian/foster one for the child
            if r and any(fid2 != fid and k in FAM.get(fid2, {}).get('chil', []) and fid2 not in ki.get('famc_rel', {})
                         for fid2 in i.get('fams', [])):
                continue                               # listed once, under the family they were born to (James: Albert Carl's five)
            c = {'n': clean_name(ki.get('name')), 'y': years(k), 'bp': place(ki.get('birt_plac')), 'dp': place(ki.get('deat_plac'))}
            if r: c['r'] = r
            if k in P: c['i'] = k
            elif living_other(k, [by, year(INDI.get(sp or '', {}).get('birt_date'))]): c['lv'] = 1
            kids.append(c)
        kids.sort(key=lambda c: year(c['y']) or 9999)
        fam['k'] = kids
        fams.append(fam)
    fams.sort(key=lambda f: year((f.get('m') or [''])[0]) or 9999)
    pr['f'] = fams
    # siblings: the other children of the birth family (the first family not marked
    # adopted/guardian/step/foster), as children are listed; half-siblings not included
    rel = i.get('famc_rel', {})
    birth_fam = next((fc for fc in i.get('famc', []) if fc not in rel), None)
    if birth_fam:
        pf = FAM.get(birth_fam, {})
        pyears = [year(INDI.get(x, {}).get('birt_date')) for x in (pf.get('husb'), pf.get('wife')) if x]
        sibs = []
        for k in pf.get('chil', []):
            if k == pid: continue
            ki = INDI.get(k, {})
            c = {'n': clean_name(ki.get('name')), 'y': years(k), 'bp': place(ki.get('birt_plac')), 'dp': place(ki.get('deat_plac'))}
            if k in P: c['i'] = k
            elif living_other(k, pyears): c['lv'] = 1
            sibs.append(c)
        sibs.sort(key=lambda c: year(c['y']) or 9999)
        if sibs: pr['sb'] = sibs
    # timeline
    t = []
    if b: t.append([year(b['date']), date_text(b['date']), 'born', place(b['plac'])])
    last = None
    resi_notes = {(x.get('DATE'), x.get('PLAC')): x.get('NOTE') or '' for x in blocks(pid, ('RESI',))}
    for e in ev:
        if e['type'] == 'RESI' and e.get('date') and e.get('plac'):
            rn = resi_notes.get((e.get('date'), e.get('plac')), '')
            y, p = year(e['date']), place(e['plac'])
            if not y: continue
            if last and last[3] == p and last[2] == 'lived':
                last[5] = y; last[4] = last[4] or rn; continue   # the same place again: one entry with a range
            last = [y, date_text(e['date']), 'lived', p, rn, y]; t.append(last)
        elif e['type'] == 'MARR':
            sp = next((clean_name(INDI.get(x, {}).get('name')) for fid in i.get('fams', [])
                       for x in (FAM.get(fid, {}).get('husb'), FAM.get(fid, {}).get('wife')) if x and x != pid), '')
            t.append([year(e.get('date')), date_text(e.get('date')), 'married', place(e.get('plac'))])
        elif e['type'] == 'MILT' and (e.get('date') or e.get('plac')):
            t.append([year(e.get('date')), date_text(e.get('date')), 'military', place(e.get('plac'))])
    for x in blocks(pid, ('EVEN', 'OCCU')):
        ty = (x.get('TYPE') or x['v'] or '').strip()
        if not ty or ty.upper().startswith('SPECULATIVE'): continue      # James marks his own guesses
        note = x.get('NOTE') or ''
        url = note if note.startswith('http') else ''
        t.append([year(x.get('DATE')), date_text(x.get('DATE')), ('Occupation: ' if x['t'] == 'OCCU' else '') + ty,
                  place(x.get('PLAC')), '' if url else note, url])
    if d: t.append([year(d['date']), date_text(d['date']), 'died', place(d['plac'])])
    if bu: t.append([year(d and d['date']), '', 'buried', place(bu['PLAC'])])
    for row in t:
        if row[2] == 'lived' and len(row) > 5 and row[5] and row[5] != row[0]:
            row[1] = f'{row[0]}–{row[5]}'
    def norm(r):                                   # [year, date, kind, place] + [note] or [note, url]
        note = (r[4] if len(r) > 4 and r[4] else '').strip()
        url = r[5] if len(r) > 5 and r[2] != 'lived' and isinstance(r[5], str) else ''
        if note.startswith('http'): note, url = '', note
        url = url.split()[0] if url else ''          # a note may hold several links; keep the first
        if TALLY.search(note): note = ''            # census tallies ("2 males under 10 ...")
        return r[:4] + ([note, url] if url else [note] if note else [])
    t = [norm(r) for r in t]
    order = {'born': 0, 'died': 8, 'buried': 9}
    t.sort(key=lambda r: (r[0] if r[0] is not None else 99999, order.get(r[2], 5)))
    pr['t'] = t
    # research notes (the tree's notes on the person that aren't just links)
    nts = []
    for l in recs.get(pid, []):
        if l.startswith('1 NOTE ') and not l[7:].startswith('http'): nts.append(l[7:].strip())
    for e in blocks(pid, ('BIRT', 'DEAT', 'BURI')):
        if e.get('NOTE') and not e['NOTE'].startswith('http') and len(e['NOTE']) > 40: nts.append(e['NOTE'].strip())
    if nts: pr['nt'] = list(dict.fromkeys(nts))
    srcs = []
    for s in sources_of(pid):
        if s not in src_index: src_index[s] = len(src_list); src_list.append(s)
        srcs.append(src_index[s])
    pr['r'] = srcs
    if pid in STORIES: pr['st'] = STORIES[pid]
    if pid in PHOTOS and pid not in LIVING:
        ph = PHOTOS[pid]
        if not (PHOTO_DIR / ph['file']).exists(): raise SystemExit(f"photos.json names a missing file: {ph['file']}")
        pr['ph'] = ['photos/' + ph['file'], ph['source']]
    return pr


LIVING = living_ids(GRAPH, INDI)


def main():
    people = {pid: profile(pid) for pid in sorted(P)}
    held = [PHOTOS[p]['name'] for p in PHOTOS if p in LIVING]
    if held: print(f'{len(held)} photos of living people held back (not published)')
    missing = [p for p in PHOTOS if p not in P]
    if missing: raise SystemExit(f'photos.json names people not on the map: {missing}')
    missing = [pid for pid in STORIES if pid not in P]
    if missing: raise SystemExit(f'stories.py names people not on the map: {missing}')
    OUT.write_text(json.dumps({'sources': src_list, 'people': people}, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')
    n_lv = sum(1 for p in people.values() for f in p['f'] for c in f['k'] + ([f['sp']] if 'sp' in f else []) if c.get('lv'))
    print(f'{len(people)} profiles, {len(src_list)} distinct record titles, {len(STORIES)} written stories, '
          f'{n_lv} living children/spouses off the map; {sum(1 for p in people.values() if "ph" in p)} portraits; '
          f'{OUT.stat().st_size // 1024} KB')


if __name__ == '__main__':
    main()
