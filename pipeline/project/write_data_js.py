"""
Write the page's data file (data.js) from the pipeline's output. This
replaced graft.py (retired) when the data moved out of index.html into its
own file.

  python pipeline/project/write_data_js.py data.js

The nine generated arrays (ROUTES, CLUSTERS, PLACES, SEARCH_INDEX, GRAPH,
PERSON_LEGS, CORRIDORS, MILITARY, NOTABLE) come from pipeline/build2/*.json, serialised exactly as
graft.py did, except that living people are hidden and their details written
encrypted as PRIVATE (see privacy.py; needs HM_PASSPHRASE). VB (the default view), which the pipeline doesn't produce, is
copied byte for byte from the existing data.js. (BASEMAP and REF_CITIES,
used only by the pre-MapLibre page, were dropped from data.js; legacy.html
keeps its own copies inline.) Declarations keep their order, one per line.

Run the pipeline and diff_shipped.py first (see pipeline/RUNBOOK.md).
"""
import os as _os
_ORIG_CWD = _os.getcwd()
PROJECT_DIR = _os.path.dirname(_os.path.abspath(__file__))
BUILD_DIR = _os.path.join(_os.path.dirname(PROJECT_DIR), "build2")
import json, sys, re
sys.path.insert(0, PROJECT_DIR)
import privacy

if len(sys.argv) != 2:
    raise SystemExit('usage: python pipeline/project/write_data_js.py <path/to/data.js>')
path = _os.path.join(_ORIG_CWD, sys.argv[1])
# data_ext.js: the extended run's arrays (core + cousins; extset.py, run_extended.sh). Its profiles go to
# profiles_ext.js; the living's portraits and the relatives index belong to the core run and are left alone.
EXT = '_ext' in _os.path.basename(path)
_anc = json.load(open(_os.path.join(PROJECT_DIR, 'ancestors.json'), encoding='utf-8'))
if EXT != bool(_anc.get('extended')):
    raise SystemExit(f'FAIL: the pipeline output on disk is from the {"extended" if _anc.get("extended") else "core"} run; '
                     f'{_os.path.basename(path)} needs the other one (see run_extended.sh)')
if EXT and not _os.path.exists(path):
    import shutil; shutil.copyfile(_os.path.join(_os.path.dirname(path), 'data.js'), path)      # for the header and VB

ORDER = ['ROUTES', 'CLUSTERS', 'PLACES', 'VB', 'SEARCH_INDEX', 'GRAPH', 'PERSON_LEGS', 'CORRIDORS', 'MILITARY', 'NOTABLE', 'PRIVATE']
GENERATED = {'ROUTES': 'routes_prepared.json', 'CLUSTERS': 'clusters_prepared.json', 'PLACES': 'places_prepared.json',
             'SEARCH_INDEX': 'search_index.json', 'GRAPH': 'person_graph.json', 'PERSON_LEGS': 'person_legs.json',
             'CORRIDORS': 'corridors_prepared.json', 'MILITARY': 'military_prepared.json',
             'NOTABLE': 'notable_prepared.json'}

old = open(path, encoding='utf-8').read().split('\n')
header, lines = [], {}
for line in old:
    m = re.match(r'const (\w+) = ', line)
    if m:
        if m.group(1) in lines: raise SystemExit(f'FAIL: {m.group(1)} declared twice in {path}')
        lines[m.group(1)] = line
    elif not lines and line.startswith('//'):
        header.append(line)
missing = [n for n in ORDER if n not in lines and n not in GENERATED and n != 'PRIVATE']
if missing: raise SystemExit(f'FAIL: {path} lacks {missing}')

arrays = {name: json.load(open(_os.path.join(BUILD_DIR, f), encoding='utf-8')) for name, f in GENERATED.items()}
INDI = json.load(open(_os.path.join(PROJECT_DIR, 'indi.json'), encoding='utf-8'))
FAM = json.load(open(_os.path.join(PROJECT_DIR, 'fam.json'), encoding='utf-8'))
living = privacy.living_ids(arrays['GRAPH'], INDI)
profiles = json.load(open(_os.path.join(BUILD_DIR, 'profiles_prepared.json'), encoding='utf-8'))
private = privacy.redact_profiles(profiles, living, privacy.redact(arrays, living))

# Living people named in the tree's own text (2026-10-02): a research note on an ancestor read "ancestor of
# <a living cousin> (through his mother <another>)". Anyone living anywhere in the tree is taken out of the
# published notes and event titles, by full name or first + last name, unless a dead person bears the same name.
_name = lambda i: re.sub(r'\s+', ' ', (INDI[i].get('name') or '').replace('/', '')).strip()
def _variants(n):
    w = n.split()
    return {n} | ({w[0] + ' ' + w[-1]} if len(w) > 2 else set())
all_living = privacy.living_relatives(INDI, FAM, living, set(arrays['GRAPH']['people']))
dead_names = {v for i in INDI if i not in all_living for v in _variants(_name(i))}
# only people with a birth date in the living range: an undated person the cautious rule calls living may be
# an 18th-century name in a quotation ("Katherine Kelly, aged 73 ... 1838")
live_names = {v for i in all_living if (privacy._year(INDI[i].get('birt_date')) or 0) >= privacy.LIVING_BORN_FROM
              for v in _variants(_name(i)) if len(v.split()) >= 2 and len(v) >= 8} - dead_names
_scrub = re.compile('|'.join(re.escape(n) for n in sorted(live_names, key=len, reverse=True))) if live_names else None
scrubbed = 0
def _clean(s):
    global scrubbed
    if not _scrub or not isinstance(s, str): return s
    # ... unless the sentence is plainly about the past ("Katherine Kelly, aged 73 ... on 7 Mar 1838"): a namesake
    def sub(m):
        global scrubbed
        a = max(s.rfind('.', 0, m.start()), s.rfind(chr(10), 0, m.start())) + 1
        b = min([x for x in (s.find('. ', m.end()), s.find(chr(10), m.end())) if x >= 0] or [len(s)])
        if re.search(r'\b1[5-8]\d\d\b', s[a:b]): return m.group(0)
        scrubbed += 1
        return 'a living relative'
    return _scrub.sub(sub, s)
for pr in profiles['people'].values():
    if pr.get('nt'): pr['nt'] = [_clean(x) for x in pr['nt']]
    for e in pr.get('t', []):
        for k in (2, 4):
            if len(e) > k: e[k] = _clean(e[k])
print(f'{scrubbed} mentions of living people taken out of published notes and event titles')

off_map = [c['n'] for p in private['pfam'].values() for f in p for c in f['k'] + ([f['sp']] if 'sp' in f else []) if c.get('lv')] + \
          [c['n'] for s in private['psib'].values() for c in s if c.get('lv')]
arrays['PRIVATE'] = privacy.encrypt(private, privacy.password())
print(f'{len(living)} living people hidden; their details encrypted in PRIVATE')
public = json.dumps({k: v for k, v in arrays.items() if k != 'PRIVATE'}, ensure_ascii=False) + json.dumps(profiles, ensure_ascii=False)
hidden_graph = privacy.decrypt(arrays['PRIVATE'], privacy.password())['graph']
core_ids = set(_anc.get('core') or hidden_graph)
# the core's living (the immediate family): their names must not appear anywhere, as before
strict = {v['name'] for pid, v in hidden_graph.items() if pid in core_ids} | (set() if EXT else set(off_map))
leak = [n for n in strict if n and n in public]
# the extended run's living cousins: a name counts as leaked unless every appearance is a dead namesake's
# (a Benjamin Askew born 2001 and the one born 1747), and one-word names can't be told apart at all
def _leaks(n):
    if len(n.split()) < 2 or n not in public: return False
    rest = public
    for d in sorted((d for d in dead_names if n in d), key=len, reverse=True): rest = rest.replace(d, '')
    return n in rest
if EXT:
    all_dead_full = {_name(i) for i in INDI if i not in all_living}
    dead_names |= all_dead_full
    leak += [n for n in {v['name'] for pid, v in hidden_graph.items() if pid not in core_ids} | set(off_map) if n and _leaks(n)]
if leak: raise SystemExit(f'FAIL: living names still in the public data: {len(leak)}: ' + '; '.join(sorted(n.split()[0] + ' ...' for n in leak)[:8]))
# the profiles, loaded by the page only when one is opened
ppath = _os.path.join(_os.path.dirname(path), 'profiles_ext.js' if EXT else 'profiles.js')
with open(ppath + '.tmp', 'w', encoding='utf-8', newline='\n') as fh:
    fh.write('// generated by pipeline/project/write_data_js.py from build2/profiles_prepared.json; living people hidden (privacy.py)\n')
    fh.write('const PROFILES = ' + json.dumps(profiles, separators=(',', ':'), ensure_ascii=False) + ';\n')
_os.replace(ppath + '.tmp', ppath)
print('wrote', ppath, _os.path.getsize(ppath), 'bytes')
# living people's portraits: photos_private/<id>.jpg (git-ignored, never published as is),
# encrypted like PRIVATE into private_photos.js, which the page loads only once unlocked
import base64
pdir = _os.path.join(_os.path.dirname(path), 'photos_private')
if EXT:
    pass
elif _os.path.isdir(pdir) and _os.listdir(pdir):
    shots = {'@' + f[:-4] + '@': base64.b64encode(open(_os.path.join(pdir, f), 'rb').read()).decode()
             for f in sorted(_os.listdir(pdir)) if f.endswith('.jpg')}
    stray = [k for k in shots if k not in living]
    if stray: raise SystemExit(f'FAIL: photos_private/ holds people who are not living (publish them in photos/): {stray}')
    qpath = _os.path.join(_os.path.dirname(path), 'private_photos.js')
    with open(qpath + '.tmp', 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('// generated by pipeline/project/write_data_js.py from photos_private/ (git-ignored); encrypted, see privacy.py\n')
        fh.write('const PRIVATE_PHOTOS = ' + json.dumps(privacy.encrypt(shots, privacy.password()), separators=(',', ':')) + ';\n')
    _os.replace(qpath + '.tmp', qpath)
    print(f'{len(shots)} living people\'s portraits encrypted ->', qpath)
else:
    print('photos_private/ is empty or missing: private_photos.js left as it was')
# everyone in the GEDCOM, for the Ask page (build_relatives.py): the living's names and
# years blanked and encrypted like PRIVATE; loaded by the page only when someone asks
rel = json.load(open(_os.path.join(BUILD_DIR, 'relatives_prepared.json'), encoding='utf-8')) if not EXT else None
while rel is not None:
    hidden = {}
    for k in rel.pop('lv'):
        hidden[str(k)] = [rel['n'][k], rel['b'][k], rel['d'][k]]
        rel['n'][k], rel['b'][k], rel['d'][k] = '', 0, 0
    map_living = {pid.strip('@') for pid in living}
    if any(rel['n'][k] for k, i in enumerate(rel['id']) if i in map_living):
        raise SystemExit('FAIL: a living person on the map is named in relatives.js')
    rel['lv'] = privacy.encrypt(hidden, privacy.password())
    rpath = _os.path.join(_os.path.dirname(path), 'relatives.js')
    with open(rpath + '.tmp', 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('// generated by pipeline/project/write_data_js.py from build2/relatives_prepared.json; living people encrypted (privacy.py)\n')
        fh.write('const RELATIVES = ' + json.dumps(rel, separators=(',', ':'), ensure_ascii=False) + ';\n')
    _os.replace(rpath + '.tmp', rpath)
    print(f'{len(hidden)} living relatives hidden ->', rpath, _os.path.getsize(rpath), 'bytes')
    break
for name, data in arrays.items():
    new = f'const {name} = ' + json.dumps(data, separators=(',', ':'), ensure_ascii=False) + ';'
    was = lines.get(name, '')
    print(f'{name}: {len(was)} -> {len(new)} chars' + ('  (unchanged)' if new == was else ''))
    lines[name] = new

out = '\n'.join(header + [lines[n] for n in ORDER]) + '\n'
tmp = path + '.tmp'
with open(tmp, 'w', encoding='utf-8', newline='\n') as fh: fh.write(out)
_os.replace(tmp, path)
print('wrote', path, len(out.encode('utf-8')), 'bytes')
