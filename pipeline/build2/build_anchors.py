import os as _os
BUILD_DIR = _os.path.dirname(_os.path.abspath(__file__))
PROJECT_DIR = _os.path.join(_os.path.dirname(BUILD_DIR), "project")
_os.chdir(BUILD_DIR)  # scripts read/write their own folder regardless of where they're launched from
import json, sys
sys.setrecursionlimit(5000)

with open(_os.path.join(PROJECT_DIR, "indi.json")) as f: indi = json.load(f)
with open(_os.path.join(PROJECT_DIR, "fam.json")) as f: fam = json.load(f)
with open(_os.path.join(PROJECT_DIR, "ancestors.json")) as f: anc_data = json.load(f)
with open(_os.path.join(PROJECT_DIR, "legs.json")) as f: legs = json.load(f)
with open(_os.path.join(PROJECT_DIR, "migration_routes.geojson")) as f: routes_geo = json.load(f)

james_id = anc_data["james_id"]
direct_ancestors = set(anc_data["direct_ancestors"])
all_people = direct_ancestors | {james_id}

def parents_of(pid):
    out = []
    for fc in indi[pid].get("famc", []):
        f = fam.get(fc)
        if not f: continue
        for p in (f.get("husb"), f.get("wife")):
            if p and p in all_people: out.append(p)
    return out

depth_memo = {}
def depth(pid):
    if pid in depth_memo: return depth_memo[pid]
    ps = parents_of(pid)
    d = 0 if not ps else 1 + max(depth(p) for p in ps)
    depth_memo[pid] = d
    return d
for pid in all_people: depth(pid)

def deepest_ancestor_chain(pid):
    chain = [pid]; cur = pid
    while True:
        ps = parents_of(cur)
        if not ps: break
        nxt = max(ps, key=lambda p: depth(p))
        chain.append(nxt); cur = nxt
    return chain

child_toward_james = {}
for fid, f in fam.items():
    child_ids = [c for c in f.get("chil", []) if c in all_people]
    if not child_ids: continue
    for parent in (f.get("husb"), f.get("wife")):
        if parent in all_people:
            for c in child_ids:
                child_toward_james.setdefault(parent, c)

def descendant_chain_to_james(pid):
    chain = [pid]; cur = pid; seen = {pid}
    while cur != james_id:
        nxt = child_toward_james.get(cur)
        if not nxt or nxt in seen: break
        chain.append(nxt); seen.add(nxt); cur = nxt
    return chain

legs_by_key = {}  # (from_place, to_place) -> list of legs
for l in legs:
    legs_by_key.setdefault((l["from_place"], l["to_place"]), []).append(l)

# --- era-aware anchor: for each geojson route feature, only consider legs
# whose year actually falls in THIS feature's min/max year range, so a
# place-pair that was era-split still gets the right anchor per era ---
route_anchor = {}  # index into routes_geo["features"] -> anchor person_id
route_all_people = {}  # index -> list of ALL person_ids who took this leg (not just the anchor)
for i, feat in enumerate(routes_geo["features"]):
    p = feat["properties"]
    key = (p["from_place"], p["to_place"])
    candidates = [l for l in legs_by_key.get(key, [])
                  if p["min_year"] <= l["to_year"] <= p["max_year"]]
    if not candidates:
        continue
    best = max(candidates, key=lambda l: depth(l["person_id"]))
    route_anchor[i] = best["person_id"]
    route_all_people[i] = list({l["person_id"] for l in candidates})

print(f"Routes: {len(routes_geo['features'])}, anchors resolved: {len(route_anchor)}")

legs_by_person = {}
for l in legs:
    legs_by_person.setdefault(l["person_id"], []).append(l)
for pid in legs_by_person:
    legs_by_person[pid].sort(key=lambda l: l["leg_order"])

def full_thread(anchor_pid):
    ancestors_part = list(reversed(deepest_ancestor_chain(anchor_pid)))
    descendants_part = descendant_chain_to_james(anchor_pid)[1:]
    person_chain = ancestors_part + descendants_part
    seg_list = []
    for pid in person_chain:
        for l in legs_by_person.get(pid, []):
            seg_list.append({"person": l["person_name"], "from": l["from_place"], "to": l["to_place"],
                              "from_lat": l["from_lat"], "from_lon": l["from_lon"],
                              "to_lat": l["to_lat"], "to_lon": l["to_lon"], "year": l["to_year"]})
    return seg_list

used_anchors = set(route_anchor.values())
all_people_with_legs = set(legs_by_person.keys())
threads = {pid: full_thread(pid) for pid in all_people_with_legs}
print(f"Distinct anchors currently used by routes: {len(used_anchors)}")
print(f"Threads built (everyone with legs, for search): {len(threads)}")

with open("route_anchor_by_index.json", "w") as f:
    json.dump({str(k): v for k, v in route_anchor.items()}, f)
with open("route_all_people_by_index.json", "w") as f:
    json.dump({str(k): v for k, v in route_all_people.items()}, f)
with open("thread_data.json", "w") as f:
    json.dump(threads, f, separators=(',',':'))
print("Saved route_anchor_by_index.json and thread_data.json")
