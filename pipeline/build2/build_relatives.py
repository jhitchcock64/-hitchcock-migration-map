"""
Stage 12: an index of everyone in the GEDCOM (not only the map's ancestors), for
the Ask page (index.html): "who are you?" and "how am I related to ...?" across
the whole tree. Names, birth and death years and family links only; no places,
notes or records (James, 2026-09-29: fine to publish the dead; the living are
hidden like everywhere else). The page loads it only when someone asks.

Reads stage 1's indi.json and fam.json and GRAPH. Writes relatives_prepared.json,
columns by index:

  { id: [pid without the @s], n: [name], b: [birth year or 0], d: [death year, 0 if
    none recorded, -1 if dead with no year], s: 'MF?..', f: [father index or -1],
    m: [mother index or -1], r: {index: 'adopted'|'step'|... when the parents shown
    aren't the birth parents}, sp: [i, j, i, j, ...] couples, lv: [living indices] }

write_data_js.py blanks the living's names and years (privacy.living_relatives)
and encrypts them into relatives.js.
"""
import json, re, sys, pathlib

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = HERE.parent / 'project'
sys.path.insert(0, str(PROJECT))
import privacy

INDI = json.load(open(PROJECT / 'indi.json', encoding='utf-8'))
FAM = json.load(open(PROJECT / 'fam.json', encoding='utf-8'))
GRAPH = json.load(open(HERE / 'person_graph.json', encoding='utf-8'))

ids = sorted(INDI)
at = {pid: k for k, pid in enumerate(ids)}
name = lambda v: re.sub(r'\s+', ' ', (v.get('name') or '').replace('/', '')).strip()
out = {'id': [pid.strip('@') for pid in ids], 'n': [], 'b': [], 'd': [], 's': '', 'f': [], 'm': [], 'r': {}, 'sp': []}
sexes = []
for k, pid in enumerate(ids):
    v = INDI[pid]
    out['n'].append(name(v))
    out['b'].append(privacy._year(v.get('birt_date')) or 0)
    dy = privacy._year(v.get('deat_date'))
    out['d'].append(dy or (-1 if v.get('deat_date') or v.get('deat_plac') else 0))
    sexes.append(v.get('sex') if v.get('sex') in ('M', 'F') else '?')
    # the parents shown: the first birth family, else the first family (and say which kind)
    rel = v.get('famc_rel') or {}
    famc = [f for f in v.get('famc', []) if f in FAM]
    pick = next((f for f in famc if not rel.get(f)), famc[0] if famc else None)
    fa = FAM[pick].get('husb') if pick else None
    mo = FAM[pick].get('wife') if pick else None
    out['f'].append(at.get(fa, -1)); out['m'].append(at.get(mo, -1))
    if pick and rel.get(pick): out['r'][str(k)] = rel[pick]
out['s'] = ''.join(sexes)
for f in sorted(FAM):
    h, w = FAM[f].get('husb'), FAM[f].get('wife')
    if h in at and w in at: out['sp'] += [at[h], at[w]]

# x: who is in the extended data (data_ext.js) but not the core map, so the Viewing-as button knows to load it
from extset import extended
_anc = json.load(open(PROJECT / 'ancestors.json', encoding='utf-8'))
_core = set(_anc.get('core') or [_anc['james_id']] + _anc['direct_ancestors'])
_ext, _ = extended(INDI, FAM, {i: g for i, g in _anc['generation_of'].items() if i in _core})
out['x'] = sorted(at[i] for i in _ext if i in at)
on_map = set(GRAPH['people']) if not _anc.get('extended') else _core & set(GRAPH['people'])
living = privacy.living_relatives(INDI, FAM, privacy.living_ids(GRAPH, INDI), on_map)
out['lv'] = sorted(at[i] for i in living if i in at)
json.dump(out, open(HERE / 'relatives_prepared.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

undated = sum(1 for k in range(len(ids)) if not out['b'][k] and not out['d'][k])
print(f'{len(ids)} people, {len(out["sp"]) // 2} couples, {len(on_map)} on the map')
print(f'{len(out["lv"])} treated as living ({sum(1 for i in living if i in on_map)} of them on the map); {undated} with no dates at all')
print(f'{len(out["r"])} shown with non-birth parents')
