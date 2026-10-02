"""
Builds gazetteer.json.gz, the geocoder's fallback for places its hand-built tables
don't know (added 2026-10-02, when the map was extended to cousins who lived all over
the country; before that every place was one a direct ancestor had lived in).

  python pipeline/project/build_gazetteer.py        (rerun only to refresh the sources)

Sources, in pipeline/basemap/cache/ (git-ignored; all public domain):
  2024_Gaz_place_national.zip   US Census Bureau Gazetteer of places
      https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_place_national.zip
  2024_Gaz_cousubs_national.zip   US Census Bureau Gazetteer of county subdivisions (towns and townships)
      https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_cousubs_national.zip
  cb_2023_us_county_500k.zip   US Census county boundaries (already used by build_basemap.py)
  ne_10m_populated_places_simple.geojson   Natural Earth populated places (the world's larger towns)

Output (committed, so a rebuild gives the same map on any machine):
  { town:   {"name|state": [[lat, lon, land area km2], ...]}   several where a state has namesakes
    county: {"name|state": [lat, lon]}                         centre of the largest part
    world:  {"name|country or province": [lat, lon]}           outside the US
    country: {"name": [lat, lon]} }                            every country, by its usual names
Names are normalised by norm() (lower case, no periods, "saint" -> "st").
"""
import gzip, json, pathlib, re, sys, zipfile
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
CACHE = HERE.parent / 'basemap' / 'cache'
sys.path.insert(0, str(HERE))
from geocoder import STATE_ABBREV, gaz_norm as norm

LSAD = re.compile(r'\s+(city and borough|consolidated government|metropolitan government|metro government|unified government|'
                  r'urban county|city|town|village|borough|municipality|CDP|corporation|plantation|comunidad|zona urbana)$')

towns = {}
with zipfile.ZipFile(CACHE / '2024_Gaz_place_national.zip') as z:
    rows = z.read('2024_Gaz_place_national.txt').decode('utf-8', 'replace').split('\n')
head = [h.strip() for h in rows[0].split('\t')]
ix = {h: i for i, h in enumerate(head)}
for line in rows[1:]:
    c = [x.strip() for x in line.split('\t')]
    if len(c) < len(head): continue
    st = STATE_ABBREV.get(c[ix['USPS']].lower())
    if not st: continue                                   # Puerto Rico and the island areas
    name = c[ix['NAME']].replace('(balance)', '').strip()
    base = name
    for _ in range(2): base = LSAD.sub('', base).strip()
    names = {base}
    # consolidated governments: "Nashville-Davidson", "Louisville/Jefferson County", "Lexington-Fayette"
    if base != name and re.search(r'government|urban county', name): names.add(re.split(r'[-/]', base)[0].strip())
    if base.startswith('Urban '): names.add(base[6:])     # "Urban Honolulu"
    rec = [round(float(c[ix['INTPTLAT']]), 4), round(float(c[ix['INTPTLONG']]), 4), round(int(c[ix['ALAND']]) / 1e6, 1)]
    for n in names:
        towns.setdefault(f'{norm(n)}|{st}', []).append(rec)
for k in towns: towns[k].sort(key=lambda r: -r[2])      # the largest first

# New England, New York, New Jersey and Pennsylvania: the town or township is the unit people lived in, and many
# are not Census "places" (Weston MA, Strafford VT, Wayne NJ). Added only where the state has no place of the name.
TOWN_STATES = {'CT', 'ME', 'MA', 'NH', 'RI', 'VT', 'NY', 'NJ', 'PA'}
SUBDIV = re.compile(r'\s+(town|township|borough|city|village|plantation|gore|grant|location|purchase)$')
subs = {}
with zipfile.ZipFile(CACHE / '2024_Gaz_cousubs_national.zip') as z:
    rows = z.read('2024_Gaz_cousubs_national.txt').decode('utf-8', 'replace').split('\n')
head = [h.strip() for h in rows[0].split('\t')]
ix = {h: i for i, h in enumerate(head)}
for line in rows[1:]:
    c = [x.strip() for x in line.split('\t')]
    if len(c) < len(head) or c[ix['USPS']] not in TOWN_STATES or c[ix['FUNCSTAT']] != 'A': continue
    name = c[ix['NAME']]
    if not SUBDIV.search(name): continue
    key = f"{norm(SUBDIV.sub('', name))}|{STATE_ABBREV[c[ix['USPS']].lower()]}"
    if key in towns: continue
    subs.setdefault(key, []).append([round(float(c[ix['INTPTLAT']]), 4), round(float(c[ix['INTPTLONG']]), 4), round(int(c[ix['ALAND']]) / 1e6, 1)])
for k, v in subs.items(): towns[k] = sorted(v, key=lambda r: -r[2])

def centre(ring):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        w = x1 * y2 - x2 * y1; a += w; cx += (x1 + x2) * w; cy += (y1 + y2) * w
    return (cy / (3 * a), cx / (3 * a), abs(a)) if a else None

counties = {}
ns = '{http://www.opengis.net/kml/2.2}'
with zipfile.ZipFile(CACHE / 'cb_2023_us_county_500k.zip') as z, z.open('cb_2023_us_county_500k.kml') as f:
    for ev, el in ET.iterparse(f):
        if el.tag != ns + 'Placemark': continue
        data = {d.get('name'): d.text for d in el.iter(ns + 'SimpleData')}
        st = STATE_ABBREV.get((data.get('STUSPS') or '').lower())
        best = None
        for poly in el.iter(ns + 'Polygon'):
            for b in poly.iter(ns + 'outerBoundaryIs'):
                for c in b.iter(ns + 'coordinates'):
                    ring = [(float(v.split(',')[0]), float(v.split(',')[1])) for v in c.text.split()]
                    r = centre(ring)
                    if r and (best is None or r[2] > best[2]): best = r
        if st and best: counties[f"{norm(data['NAME'])}|{st}"] = [round(best[0], 4), round(best[1], 4)]
        el.clear()

world = {}
feats = json.load(open(CACHE / 'ne_10m_populated_places_simple.geojson', encoding='utf-8'))['features']
for ft in sorted(feats, key=lambda f: -(f['properties'].get('pop_max') or 0)):      # the larger namesake wins
    p = ft['properties']
    if p.get('adm0name') == 'United States of America': continue
    ll = [round(p['latitude'], 4), round(p['longitude'], 4)]
    for region in (p.get('adm0name'), p.get('adm1name')):
        if region: world.setdefault(f"{norm(p['name'])}|{norm(region)}", ll)

countries = {}
for ft in json.load(open(CACHE / 'ne_10m_admin_0_countries.geojson', encoding='utf-8'))['features']:
    p = ft['properties']
    if p.get('LABEL_Y') is None or p.get('ADMIN') == 'United States of America': continue
    for k in ('NAME', 'NAME_LONG', 'ADMIN', 'NAME_EN'):
        if p.get(k): countries.setdefault(norm(p[k]), [round(p['LABEL_Y'], 3), round(p['LABEL_X'], 3)])

out = {'town': dict(sorted(towns.items())), 'county': dict(sorted(counties.items())), 'world': dict(sorted(world.items())),
       'country': dict(sorted(countries.items()))}
raw = json.dumps(out, separators=(',', ':'), ensure_ascii=False, sort_keys=True).encode('utf-8')
with open(HERE / 'gazetteer.json.gz', 'wb') as fh:
    with gzip.GzipFile(fileobj=fh, mode='wb', mtime=0) as g: g.write(raw)       # mtime=0: the same bytes every run
print(f'{len(towns)} US town names, {len(counties)} counties, {len(world)} places elsewhere, {len(countries)} country names; {(HERE / "gazetteer.json.gz").stat().st_size // 1024} KB')
