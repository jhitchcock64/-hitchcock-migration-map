import json, sys
base, out = sys.argv[1], sys.argv[2]
html = open(base, encoding='utf-8').read()
B = '/home/claude/build2/'
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
    data = json.load(open(B + f))
    new = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    html = html[:v] + new + html[e:]
    print(f'{name}: replaced ({e - v} -> {len(new)} chars)')
open(out, 'w', encoding='utf-8').write(html)
print('wrote', out, len(html))
