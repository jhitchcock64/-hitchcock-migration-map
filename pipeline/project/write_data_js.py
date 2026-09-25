"""
Write the page's data file (data.js) from the pipeline's output. This
replaced graft.py (retired) when the data moved out of index.html into its
own file.

  python pipeline/project/write_data_js.py data.js

The seven generated arrays (ROUTES, CLUSTERS, PLACES, SEARCH_INDEX, GRAPH,
PERSON_LEGS, CORRIDORS) come from pipeline/build2/*.json, serialised exactly as
graft.py did. VB (the default view), which the pipeline doesn't produce, is
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

if len(sys.argv) != 2:
    raise SystemExit('usage: python pipeline/project/write_data_js.py <path/to/data.js>')
path = _os.path.join(_ORIG_CWD, sys.argv[1])

ORDER = ['ROUTES', 'CLUSTERS', 'PLACES', 'VB', 'SEARCH_INDEX', 'GRAPH', 'PERSON_LEGS', 'CORRIDORS']
GENERATED = {'ROUTES': 'routes_prepared.json', 'CLUSTERS': 'clusters_prepared.json', 'PLACES': 'places_prepared.json',
             'SEARCH_INDEX': 'search_index.json', 'GRAPH': 'person_graph.json', 'PERSON_LEGS': 'person_legs.json',
             'CORRIDORS': 'corridors_prepared.json'}

old = open(path, encoding='utf-8').read().split('\n')
header, lines = [], {}
for line in old:
    m = re.match(r'const (\w+) = ', line)
    if m:
        if m.group(1) in lines: raise SystemExit(f'FAIL: {m.group(1)} declared twice in {path}')
        lines[m.group(1)] = line
    elif not lines and line.startswith('//'):
        header.append(line)
missing = [n for n in ORDER if n not in lines and n not in GENERATED]
if missing: raise SystemExit(f'FAIL: {path} lacks {missing}')

for name, f in GENERATED.items():
    data = json.load(open(_os.path.join(BUILD_DIR, f), encoding='utf-8'))
    new = f'const {name} = ' + json.dumps(data, separators=(',', ':'), ensure_ascii=False) + ';'
    was = lines.get(name, '')
    print(f'{name}: {len(was)} -> {len(new)} chars' + ('  (unchanged)' if new == was else ''))
    lines[name] = new

out = '\n'.join(header + [lines[n] for n in ORDER]) + '\n'
tmp = path + '.tmp'
with open(tmp, 'w', encoding='utf-8', newline='\n') as fh: fh.write(out)
_os.replace(tmp, path)
print('wrote', path, len(out.encode('utf-8')), 'bytes')
