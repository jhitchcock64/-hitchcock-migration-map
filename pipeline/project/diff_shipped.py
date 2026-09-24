import json, sys
shipped_html = sys.argv[1] if len(sys.argv) > 1 else '/tmp/shipped_v14.html'
js = open(shipped_html, encoding='utf-8').read()
def const(name):
    s = js.find(f'const {name} = ') + len(f'const {name} = '); d = 0
    for i in range(s, len(js)):
        if js[i] in '{[': d += 1
        elif js[i] in '}]':
            d -= 1
            if d == 0: return json.loads(js[s:i+1])
B = '/home/claude/build2/'
S = {n: const(n) for n in ['ROUTES','PLACES','GRAPH','SEARCH_INDEX','PERSON_LEGS','CLUSTERS']}
M = {'ROUTES': json.load(open(B+'routes_prepared.json')), 'PLACES': json.load(open(B+'places_prepared.json')),
     'GRAPH': json.load(open(B+'person_graph.json')), 'SEARCH_INDEX': json.load(open(B+'search_index.json')),
     'PERSON_LEGS': json.load(open(B+'person_legs.json')), 'CLUSTERS': json.load(open(B+'clusters_prepared.json'))}
for n in S:
    la = len(S[n]['people']) if n=='GRAPH' else len(S[n]); lb = len(M[n]['people']) if n=='GRAPH' else len(M[n])
    print(f'{n}: shipped={la} mine={lb}')
key = lambda r: (r['from'], r['to'], tuple(sorted(r['people'])))
sr = {key(r) for r in S['ROUTES']}; mr = {key(r) for r in M['ROUTES']}
print('routes only-shipped:', len(sr-mr), ' only-mine:', len(mr-sr))
sp = {p['label'] for p in S['PLACES']}; mp = {p['label'] for p in M['PLACES']}
print('places only-shipped:', len(sp-mp), ' only-mine:', len(mp-sp))
# per-person leg agreement
sl, ml = S['PERSON_LEGS'], M['PERSON_LEGS']
same = sum(1 for p in sl if p in ml and [(l['from'],l['to'],l['year']) for l in sl[p]] == [(l['from'],l['to'],l['year']) for l in ml[p]])
print(f'people with identical legs: {same} / {len(sl)}')
