import os as _os
BUILD_DIR = _os.path.dirname(_os.path.abspath(__file__))
PROJECT_DIR = _os.path.join(_os.path.dirname(BUILD_DIR), "project")
_os.chdir(BUILD_DIR)  # scripts read/write their own folder regardless of where they're launched from
import json, math
from collections import defaultdict

with open(_os.path.join(PROJECT_DIR, "legs.json")) as f: legs = json.load(f)
with open(_os.path.join(PROJECT_DIR, "indi.json")) as f: indi = json.load(f)
with open(_os.path.join(PROJECT_DIR, "fam.json")) as f: fam = json.load(f)
with open(_os.path.join(PROJECT_DIR, "ancestors.json")) as f: anc_data = json.load(f)
with open(_os.path.join(PROJECT_DIR, "migration_routes.geojson")) as f: routes_geo = json.load(f)

direct_ancestors = set(anc_data["direct_ancestors"])

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2-lat1); dlmb = math.radians(lon2-lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return 2*R*math.asin(math.sqrt(a))

legs_by_person = defaultdict(list)
for l in legs: legs_by_person[l["person_id"]].append(l)
for pid in legs_by_person: legs_by_person[pid].sort(key=lambda l: l["leg_order"])

pairs = set()
for fid, f in fam.items():
    husb, wife = f.get("husb"), f.get("wife")
    if husb in direct_ancestors and wife in direct_ancestors:
        pairs.add(tuple(sorted((husb, wife))))
    for parent in (husb, wife):
        if parent not in direct_ancestors: continue
        for child in f.get("chil", []):
            if child in direct_ancestors:
                pairs.add(tuple(sorted((parent, child))))

def legs_match(legsA, legsB, year_tol=3):
    matches = []
    for la in legsA:
        for lb in legsB:
            if (haversine_km(la["from_lat"],la["from_lon"],lb["from_lat"],lb["from_lon"]) < 8 and
                haversine_km(la["to_lat"],la["to_lon"],lb["to_lat"],lb["to_lon"]) < 8 and
                abs(la["to_year"] - lb["to_year"]) <= year_tol):
                matches.append((la["to_year"], lb["to_year"]))
    return matches

confirmed_group_legs = {}
for a, b in pairs:
    la, lb = legs_by_person.get(a, []), legs_by_person.get(b, [])
    if len(la) < 2 or len(lb) < 2: continue
    matches = legs_match(la, lb)
    if len(matches) >= 2:
        for la_i in la:
            for lb_i in lb:
                if (haversine_km(la_i["from_lat"],la_i["from_lon"],lb_i["from_lat"],lb_i["from_lon"]) < 8 and
                    haversine_km(la_i["to_lat"],la_i["to_lon"],lb_i["to_lat"],lb_i["to_lon"]) < 8 and
                    abs(la_i["to_year"]-lb_i["to_year"]) <= 3):
                    key = (la_i["from_place"], la_i["to_place"])
                    confirmed_group_legs.setdefault(key, set()).update([a, b])

print(f"Place-pairs with a confirmed traveling-together group: {len(confirmed_group_legs)}")

name_to_id = {}
for pid in direct_ancestors:
    name_to_id.setdefault(indi[pid]["name"].replace("/",""), pid)

route_family_tags = {}
for i, feat in enumerate(routes_geo["features"]):
    p = feat["properties"]
    key = (p["from_place"], p["to_place"])
    group_ids = confirmed_group_legs.get(key)
    if not group_ids: continue
    route_people_ids = [name_to_id.get(n) for n in p["sample_people"]]
    present = [pid for pid in route_people_ids if pid in group_ids]
    if len(present) >= 2:
        route_family_tags[i] = [indi[pid]["name"].replace("/","") for pid in present]

print(f"Routes tagged as confirmed family-travel-together: {len(route_family_tags)}")
with open("route_family_tags.json", "w") as f:
    json.dump({str(k): v for k,v in route_family_tags.items()}, f)
