"""
Copy the generated data arrays out of the live page into v2/data.js.

The v2 page loads its data from a separate classic script (data.js) instead
of carrying ~1.75 MB inline. This tool copies the nine `const NAME = ...;`
lines from index.html byte for byte: no parsing, no re-serialising, no
editing, so the arrays stay exactly what the pipeline + graft produced.
(Phase 5 of REBUILD_BRIEF.md replaces this with the pipeline writing data.js
directly.)

Usage:  python tools/export_data.py [index.html] [v2/data.js]
"""
import sys, re, pathlib

NAMES = ['BASEMAP', 'ROUTES', 'CLUSTERS', 'PLACES', 'REF_CITIES', 'VB',
         'SEARCH_INDEX', 'GRAPH', 'PERSON_LEGS']

src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'index.html')
out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else 'v2/data.js')

lines = src.read_text(encoding='utf-8').split('\n')
found = {}
for i, line in enumerate(lines):
    m = re.match(r'const (\w+) = ', line)
    if m and m.group(1) in NAMES:
        if m.group(1) in found:
            sys.exit(f'FAIL: {m.group(1)} is declared twice in {src} (lines {found[m.group(1)][0] + 1} and {i + 1})')
        found[m.group(1)] = (i, line)
missing = [n for n in NAMES if n not in found]
if missing:
    sys.exit(f'FAIL: not found in {src}: {missing}')
for n, (i, line) in found.items():
    if not line.rstrip().endswith(';'):
        sys.exit(f'FAIL: {n} (line {i + 1}) does not end with ";" -- not a single-line declaration?')

header = ('// Generated data for the migration map. Copied verbatim from the live page\n'
          f'// by tools/export_data.py. Do not hand-edit: regenerate instead.\n')
body = '\n'.join(found[n][1] for n in NAMES) + '\n'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(header + body, encoding='utf-8', newline='\n')

# verify: every exported line is byte-identical to its source line
back = out.read_text(encoding='utf-8').split('\n')
for n in NAMES:
    if found[n][1] not in back:
        sys.exit(f'FAIL: {n} differs after writing')
print(f'OK: wrote {out} ({out.stat().st_size // 1024} KB), {len(NAMES)} arrays, each byte-identical to {src}')
