import os as _os
_ORIG_CWD = _os.getcwd()
PROJECT_DIR = _os.path.dirname(_os.path.abspath(__file__))
BUILD_DIR = _os.path.join(_os.path.dirname(PROJECT_DIR), "build2")
_os.chdir(PROJECT_DIR)  # scripts read/write their own folder regardless of where they're launched from
import json, sys
base, out = (_os.path.join(_ORIG_CWD, a) for a in sys.argv[1:3])
html = open(base, encoding='utf-8').read()
B = BUILD_DIR + '/'
repl = {'ROUTES': 'routes_prepared.json', 'CLUSTERS': 'clusters_prepared.json', 'PLACES': 'places_prepared.json',
        'SEARCH_INDEX': 'search_index.json', 'GRAPH': 'person_graph.json', 'PERSON_LEGS': 'person_legs.json'}
def bounds(s, name):
    m = f'const {name} = '; st = s.find(m)
    assert st != -1 and s.count(m) == 1, name
    v = st + len(m); d = 0; q = False; esc = False
    for i in range(v, len(s)):
        c = s[i]
        if q:
            if esc: esc = False
            elif c == '\\': esc = True
            elif c == '"': q = False
            continue
        if c == '"': q = True
        elif c in '{[': d += 1
        elif c in '}]':
            d -= 1
            if d == 0: return v, i + 1
for name, f in repl.items():
    v, e = bounds(html, name)
    data = json.load(open(B + f, encoding='utf-8'))
    new = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    html = html[:v] + new + html[e:]
    print(f'{name}: replaced ({e - v} -> {len(new)} chars)')
open(out, 'w', encoding='utf-8').write(html)
print('wrote', out, len(html))
