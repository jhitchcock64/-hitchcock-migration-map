import os as _os
BUILD_DIR = _os.path.dirname(_os.path.abspath(__file__))
PROJECT_DIR = _os.path.join(_os.path.dirname(BUILD_DIR), "project")
_os.chdir(BUILD_DIR)  # scripts read/write their own folder regardless of where they're launched from
import json, math, re
from collections import defaultdict

CENTRAL_LON = -35.0
REF_LAT = 65.0
def project(lon, lat):
    shifted = ((lon - CENTRAL_LON + 180) % 360) - 180
    return round(shifted,2), round(REF_LAT - lat,2)

def is_ocean_crossing(from_lon, to_lon):
    americas = from_lon < -25
    old_world = to_lon > -20
    return (americas and old_world) or (to_lon < -25 and from_lon > -20)

# A raw great-circle is the true geometric shortest path, but for a long
# diagonal crossing (e.g. Germany -> New Orleans) that shortest path genuinely
# runs directly over New England, Ohio, and Alabama -- verified by computing
# it. Real ships couldn't sail overland, so transatlantic routes now go
# through waypoints chosen to stay over open water, verified against actual
# coastline risk zones (Florida, Cuba, Newfoundland, Nova Scotia) rather than
# assumed.
STANDARD_OCEAN_WPS = [(-48, 42), (-58, 38)]
GULF_OCEAN_WPS = [(-48, 38), (-70, 26), (-82.3, 23.9), (-85.0, 26.2), (-88.0, 28.3)]
# Scandinavian departures need their own route: the standard waypoints assume
# a Germany/England-ish starting longitude, but Sweden sits far enough
# northeast that the direct path cuts across Denmark and the British Isles
# (verified: it does, precisely, using real land polygon data rather than
# approximated boxes). This threads the Skagerrak strait (open water between
# Denmark and Norway), then swings north around Scotland.
SCANDI_OCEAN_WPS = [(10.5, 57.9), (7.5, 57.4), (4.0, 56.5), (0.0, 57.0), (-2.0, 59.3),
                     (-6.5, 61.5), (-11.0, 60.5), (-16.0, 57.0), (-48, 42), (-58, 38)]

def is_scandinavian_origin(lon, lat):
    return 8 <= lon <= 24 and 55 <= lat <= 69

# Per explicit user instruction: Swiss emigrants departed via Le Havre, and
# German emigrants via Bremen, regardless of exact origin city -- these were
# the actual historical departure ports, not the inland town itself. Both
# waypoint chains verified clear of land (France's Cotentin Peninsula near
# Cherbourg, the Netherlands, and the British Isles) using real polygon data,
# for both standard and Gulf-bound destinations.
LE_HAVRE_PREFIX = [(0.108, 49.494), (-2.0, 50.0)]
BREMEN_PREFIX = [(8.807, 53.075), (6.0, 55.0), (0.0, 57.0), (-2.0, 59.3),
                  (-6.5, 61.5), (-11.0, 60.5), (-16.0, 57.0)]

def is_swiss_origin(lon, lat):
    return 5.9 <= lon <= 10.6 and 45.8 <= lat <= 47.9

def is_german_origin(lon, lat):
    return 5.8 <= lon <= 15.1 and 47.2 <= lat <= 55.1

def is_gulf_destination(lon, lat):
    return -98 <= lon <= -80 and 25 <= lat <= 31.5

# UK/Ireland origins: a direct line from an inland British or Irish town to
# the standard mid-Atlantic waypoints visually sweeps across the whole island
# (verified: for an East Anglia or Yorkshire origin, it does) rather than
# making the short, realistic hop to the nearest coast that an actual emigrant
# journey would show. Two zones, split roughly along the Pennines/Welsh
# border: western Britain exits directly to the west coast; southern/eastern
# Britain exits south into the Channel. Both waypoint sets verified clear of
# southern Ireland, Land's End, and the Isles of Scilly.
def is_uk_ireland_origin(lon, lat):
    return -10.7 <= lon <= 1.8 and 49.8 <= lat <= 55.9

def is_ireland_origin(lon, lat):
    return -10.7 <= lon <= -5.9 and 51.3 <= lat <= 55.5

def uk_ireland_exit_waypoints(lon, lat):
    if is_ireland_origin(lon, lat):
        # Ireland is narrow east-west: head directly offshore near the
        # origin's own latitude rather than Britain's south-then-west
        # formula, which cuts through the Irish landmass for inland origins
        return [(-11.5, lat - 0.5)]
    elif lon <= -2.3:
        return [(-8.0, max(lat - 2.5, 49.4)), (-11.5, max(lat - 4.0, 49.7))]
    else:
        return [(lon, 50.0), (-5.5, 49.3), (-10.5, 49.8)]

# Connecticut / Long Island Sound destinations: the standard waypoints
# approach from the open Atlantic, and a direct line to a Sound-side town cuts
# across Long Island. Real ships passed south of the island, then rounded
# Montauk Point into the Sound.
def is_ct_sound_destination(lon, lat):
    return -73.7 <= lon <= -71.7 and 40.9 <= lat <= 41.5

CT_SOUND_WPS = [(-71.9, 40.3), (-71.2, 41.15)]

# Chesapeake Bay region: essentially all of Virginia and Maryland (the user's
# instruction: "anywhere in that region, so long as it's not explicitly a
# port on the open Atlantic Ocean"), matching the St. Lawrence pattern -- a
# single shared trunk from the open ocean into the bay, with only the final
# per-destination segment diverging. The dense run of waypoints from the open
# ocean to the mouth was necessary: the coastline near the York/James rivers
# is complex and fingered, and sparser waypoint chains kept clipping a
# peninsula tip regardless of exact placement. Real ships entered via the
# mouth (between Cape Charles and Cape Henry), then the bay itself widens out
# cleanly north of it.
def is_chesapeake_destination(lon, lat):
    return -80.0 <= lon <= -75.5 and 36.5 <= lat <= 39.7

CHESAPEAKE_WPS = [(-65, 37.0), (-70, 37.0), (-73, 37.0), (-75, 37.0), (-76.0, 37.0),
                   (-76.25, 37.0), (-76.2, 37.5), (-76.15, 38.0), (-76.1, 38.2)]

# Massachusetts/Cape Cod Bay destinations (Boston, Cambridge, Braintree,
# Plymouth, Duxbury, Ipswich, etc.) north of the Cape's base: the standard
# approach cuts across the Cape's arm. Real ships rounded the tip
# (Provincetown) before turning into the bay. Restricted to the north side --
# destinations already south/west of the Cape (Bristol, New Bedford, Fall
# River) are approached naturally from the open Atlantic/Narragansett Bay and
# need no detour; per the user, those should NOT be routed through this.
def is_cape_cod_north_destination(lon, lat):
    return -71.3 <= lon <= -69.9 and 41.85 <= lat <= 42.75

CAPE_COD_WPS = [(-65, 42.0), (-68, 42.0), (-69.8, 42.05), (-70.3, 42.2), (-70.6, 42.3)]


# Canadian destinations (St. Lawrence corridor: Quebec, Montreal, Toronto via
# the Seaway) get their own route -- the standard Atlantic waypoints approach
# the US coast, and a direct line from there to somewhere like Toronto cuts
# straight across New York State. Real ships entered via the Cabot Strait
# (between Newfoundland and Cape Breton), then followed the Gulf and River of
# St. Lawrence. Waypoints stay in the wide, unambiguous parts of the
# waterway, anchored to known landmark coordinates (Quebec City, Montreal).
STLAWRENCE_WPS = [(-52.0, 45.3), (-56.5, 45.8), (-59.6, 47.15), (-62.0, 48.54),
                   (-64.0, 48.84), (-65.5, 49.78), (-67.0, 49.46), (-68.5, 48.78),
                   (-69.5, 48.14), (-69.9, 47.72), (-70.7, 47.08), (-70.9, 47.03),
                   (-71.0, 46.97), (-71.1, 46.92), (-71.2, 46.82), (-71.5, 46.72),
                   (-71.7, 46.67), (-72.0, 46.61), (-72.4, 46.405), (-72.8, 46.215),
                   (-73.2, 45.975), (-73.567, 45.501), (-77.5, 43.9)]

def is_canadian_stlawrence_destination(lon, lat):
    return -85 <= lon <= -70 and 42.5 <= lat <= 47.5

def ocean_waypoints(americas_lon, americas_lat, old_world_lon=None, old_world_lat=None):
    if is_cape_cod_north_destination(americas_lon, americas_lat):
        base = STANDARD_OCEAN_WPS + CAPE_COD_WPS
    elif is_canadian_stlawrence_destination(americas_lon, americas_lat):
        base = STLAWRENCE_WPS
    elif is_gulf_destination(americas_lon, americas_lat):
        base = GULF_OCEAN_WPS
    elif is_ct_sound_destination(americas_lon, americas_lat):
        base = STANDARD_OCEAN_WPS + CT_SOUND_WPS
    elif is_chesapeake_destination(americas_lon, americas_lat):
        base = STANDARD_OCEAN_WPS + CHESAPEAKE_WPS
    else:
        base = STANDARD_OCEAN_WPS
    if old_world_lon is not None:
        if is_swiss_origin(old_world_lon, old_world_lat):
            return LE_HAVRE_PREFIX + base
        if is_german_origin(old_world_lon, old_world_lat):
            return BREMEN_PREFIX + base
        if is_scandinavian_origin(old_world_lon, old_world_lat):
            return SCANDI_OCEAN_WPS
        if is_uk_ireland_origin(old_world_lon, old_world_lat):
            return uk_ireland_exit_waypoints(old_world_lon, old_world_lat) + base
    return base



def bow_control_point(x1, y1, x2, y2, seed=0):
    dx, dy = x2-x1, y2-y1
    dist = math.hypot(dx, dy)
    if dist < 0.01: return (x1+x2)/2, (y1+y2)/2
    px, py = -dy/dist, dx/dist
    jitter = 0.85 + 0.3 * ((seed * 2654435761) % 1000) / 1000.0
    bow = min(dist * 0.16, 6.0) * jitter
    return round((x1+x2)/2 + px*bow, 2), round((y1+y2)/2 + py*bow, 2)

def region_of_label(label):
    if "," not in label:
        return label.strip().lower()
    return label.rsplit(",", 1)[-1].strip().lower()

def catmull_rom_spline(pts, samples_per_segment=8):
    """Smooth spline through 3+ control points (start, waypoint(s), end).
    Reuses the existing multi-point 'path' rendering mode -- no client-side
    changes needed, since ocean-crossing routes already render multi-point
    paths this way."""
    if len(pts) < 3:
        return pts
    p = [pts[0]] + pts + [pts[-1]]  # pad ends for Catmull-Rom tangents
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i-1], p[i], p[i+1], p[i+2]
        n = samples_per_segment if i < len(p) - 3 else samples_per_segment + 1
        for j in range(n):
            t = j / samples_per_segment
            t2, t3 = t*t, t*t*t
            x = 0.5*((2*p1[0]) + (-p0[0]+p2[0])*t + (2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*t2 + (-p0[0]+3*p1[0]-3*p2[0]+p3[0])*t3)
            y = 0.5*((2*p1[1]) + (-p0[1]+p2[1])*t + (2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2 + (-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3)
            out.append([round(x,2), round(y,2)])
    return out

# Known historical migration corridors relevant to this family's data,
# identified by analyzing actual leg frequency (Virginia->Kentucky alone
# accounts for 37 of ~625 legs -- overwhelmingly the dominant overland
# pattern -- with North Carolina->Kentucky a distant second at 9). Matched
# by state/region pair in EITHER direction; waypoints are real geographic
# features, not decorative. Coordinates are (lon, lat) to match project().
CORRIDORS = [
    # Wilderness Road via the Cumberland Gap -- by far the dominant overland
    # pattern in this dataset (VA/NC/MD/TN -> KY, 46+ legs combined)
    ({"virginia","north carolina","maryland","tennessee"}, {"kentucky"},
     [(-83.68, 36.60)]),  # Cumberland Gap (VA/KY/TN border)
    # Great Wagon Road via the Shenandoah Valley (PA <-> VA, 9 legs --
    # matches William Worthington's own documented 1769 move exactly)
    ({"pennsylvania"}, {"virginia"},
     [(-79.07, 38.15)]),  # near Staunton, VA -- central Shenandoah Valley
    # New York <-> Michigan (Raymond/Eells family, 3 legs): no land border
    # between the two, and a direct line plausibly cuts across Ontario,
    # Canada, going around the north shore of Lake Erie. Routed via
    # northern Ohio instead, staying south of the lake the whole way.
    ({"new york"}, {"michigan"},
     [(-83.56, 41.66)]),  # near Toledo, OH -- western end of Lake Erie
    # John Grove Speer's 1857 Panama-route return journey: three maritime
    # legs that a simple bow curve cuts straight across land (Baja
    # California, Costa Rica, Cuba/Hispaniola). Waypoints verified clear of
    # every coastline via the same land-polygon check used for the St.
    # Lawrence Seaway corridor.
    ({"california"}, {"mexico"},
     [(-123.5, 37.5), (-118.0, 27.0), (-108.0, 18.0)]),  # clears Baja and the mainland coast near Puerto Vallarta
    ({"mexico"}, {"panama"},
     [(-96.0, 13.0), (-84.0, 7.0), (-79.0, 6.0)]),  # clears Costa Rica's Pacific bulge and Panama's Azuero Peninsula
    ({"panama"}, {"new york"},
     [(-77.5, 13.5), (-70.0, 15.0), (-63.0, 18.0), (-68.0, 30.0)]),  # south of Jamaica/Hispaniola, east of Puerto Rico, then north
]

def corridor_waypoints(from_label, to_label):
    fr = region_of_label(from_label)
    to = region_of_label(to_label)
    for set_a, set_b, waypoints in CORRIDORS:
        if (fr in set_a and to in set_b) or (fr in set_b and to in set_a):
            return waypoints
    return None

def downsample(coords, target=10):
    if len(coords) <= target: return coords
    step = (len(coords)-1)/(target-1)
    return [coords[round(i*step)] for i in range(target)]

# ---- routes ----
with open(_os.path.join(PROJECT_DIR, "migration_routes.geojson")) as f:
    routes_geo = json.load(f)
with open("route_anchor_by_index.json") as f:
    anchor_by_idx = json.load(f)
with open("route_all_people_by_index.json") as f:
    all_people_by_idx = json.load(f)
with open("route_family_tags.json") as f:
    family_tags = json.load(f)

routes_out = []
for i, feat in enumerate(routes_geo["features"]):
    p = feat["properties"]
    coords = feat["geometry"]["coordinates"]
    from_lon, to_lon = coords[0][0], coords[-1][0]
    ocean = is_ocean_crossing(from_lon, to_lon)
    waypoints = None if ocean else corridor_waypoints(p["from_place"], p["to_place"])
    if ocean:
        from_pt, to_pt = coords[0], coords[-1]
        starts_in_americas = from_lon < -25
        americas_pt = from_pt if starts_in_americas else to_pt
        old_world_pt = to_pt if starts_in_americas else from_pt
        wps = ocean_waypoints(americas_pt[0], americas_pt[1], old_world_pt[0], old_world_pt[1])
        if starts_in_americas:
            wps = list(reversed(wps))
        x1,y1 = project(from_pt[0], from_pt[1])
        x2,y2 = project(to_pt[0], to_pt[1])
        pts = [[x1,y1]] + [[*project(wlon,wlat)] for wlon,wlat in wps] + [[x2,y2]]
        proj_coords = catmull_rom_spline(pts)
        curve = {"mode": "path", "coords": proj_coords}
    elif waypoints:
        x1,y1 = project(coords[0][0], coords[0][1])
        x2,y2 = project(coords[-1][0], coords[-1][1])
        pts = [[x1,y1]]
        for wlon, wlat in waypoints:
            wx, wy = project(wlon, wlat)
            # small deterministic jitter so many routes sharing a corridor
            # bundle together visually rather than drawing one hidden line
            jx = ((i * 2654435761) % 200 - 100) / 100.0 * 0.6
            jy = ((i * 40503 + 7) % 200 - 100) / 100.0 * 0.6
            pts.append([round(wx+jx,2), round(wy+jy,2)])
        pts.append([x2,y2])
        proj_coords = catmull_rom_spline(pts)
        curve = {"mode": "path", "coords": proj_coords}
    else:
        x1,y1 = project(coords[0][0], coords[0][1])
        x2,y2 = project(coords[-1][0], coords[-1][1])
        cx,cy = bow_control_point(x1,y1,x2,y2, seed=i)
        curve = {"mode": "bow", "x1":x1,"y1":y1,"cx":cx,"cy":cy,"x2":x2,"y2":y2}
    entry = {
        "id": f"r{i}", "curve": curve, "count": p["ancestor_count"], "mean_year": p["mean_year"],
        "min_year": p["min_year"], "max_year": p["max_year"],
        "from": p["from_place"], "to": p["to_place"], "people": p["sample_people"],
        "anchor": anchor_by_idx.get(str(i)),
        "anchor_ids": all_people_by_idx.get(str(i), []),
    }
    if str(i) in family_tags:
        entry["family_group"] = family_tags[str(i)]
    routes_out.append(entry)

# ---- oscillation detection & merge ----
# Per explicit user decision: any short-distance, repeated back-and-forth
# pattern (e.g. Henderson <-> Spottsville, KY, 18km apart) within a single
# person's own life represents a real local commuting/dual-residence
# pattern, not separate one-way journeys -- collapse each into ONE
# bidirectional marker. A single person's own A->B->A is sufficient; it
# doesn't need to be corroborated by other people also doing it. Longer-
# distance repeats (e.g. Monaghan <-> Toronto, 5000+ km) are genuinely two
# distinct journeys and stay separate.
with open(_os.path.join(PROJECT_DIR, "legs.json")) as f:
    legs = json.load(f)

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2-lat1); dlmb = math.radians(lon2-lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return 2*R*math.asin(math.sqrt(a))

OSCILLATION_MAX_KM = 50
OSCILLATION_MIN_REPEATS = 1

by_person_legs = defaultdict(list)
for l in legs:
    by_person_legs[l["person_id"]].append(l)
for pid in by_person_legs:
    by_person_legs[pid].sort(key=lambda l: l["leg_order"])

pair_repeat_count = defaultdict(int)
pair_distance = {}
for pid, ls in by_person_legs.items():
    full = [{"place": ls[0]["from_place"], "lat": ls[0]["from_lat"], "lon": ls[0]["from_lon"]}]
    for l in ls:
        full.append({"place": l["to_place"], "lat": l["to_lat"], "lon": l["to_lon"]})
    for i in range(len(full) - 2):
        a, b, c = full[i], full[i+1], full[i+2]
        if a["place"] == c["place"] and a["place"] != b["place"]:
            key = tuple(sorted([a["place"], b["place"]]))
            pair_repeat_count[key] += 1
            pair_distance[key] = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])

oscillation_pairs = {key for key, n in pair_repeat_count.items()
                      if n >= OSCILLATION_MIN_REPEATS and pair_distance[key] <= OSCILLATION_MAX_KM}
print(f"Oscillation pairs identified: {len(oscillation_pairs)}")

merged_by_key = defaultdict(list)
kept_routes = []
for r in routes_out:
    key = tuple(sorted([r["from"], r["to"]]))
    if key in oscillation_pairs:
        merged_by_key[key].append(r)
    else:
        kept_routes.append(r)

for key, members in merged_by_key.items():
    total_count = sum(m["count"] for m in members)
    all_people = []
    for m in members: all_people.extend(m["people"])
    all_anchor_ids = []
    for m in members: all_anchor_ids.extend(m.get("anchor_ids", []))
    # use the first member's geometry as the representative line (direction
    # doesn't matter for a bidirectional marker -- both ends get an arrowhead)
    base = members[0]
    merged_entry = {
        "id": base["id"] + "-osc", "curve": base["curve"], "count": total_count,
        "mean_year": sum(m["mean_year"]*m["count"] for m in members) / total_count,
        "min_year": min(m["min_year"] for m in members), "max_year": max(m["max_year"] for m in members),
        "from": key[0], "to": key[1], "people": sorted(set(all_people))[:5],
        "anchor": max(members, key=lambda m: m["count"]).get("anchor"),
        "anchor_ids": sorted(set(all_anchor_ids)),
        "oscillation": True,
    }
    fam_members = [m["family_group"] for m in members if "family_group" in m]
    if fam_members:
        merged_entry["family_group"] = sorted(set(name for fg in fam_members for name in fg))
    kept_routes.append(merged_entry)

print(f"Routes before merge: {len(routes_out)}, after: {len(kept_routes)}")
routes_out = kept_routes

# ---- clusters (for zoom-dependent aggregation) ----
# Group overland routes by (from_region, to_region). A cluster below this
# size doesn't create enough visual clutter to need aggregating -- it can
# just render as individual lines at any zoom.
MIN_CLUSTER_SIZE = 2
region_groups = defaultdict(list)
for idx, r in enumerate(routes_out):
    if r["curve"]["mode"] == "path" and not corridor_waypoints(r["from"], r["to"]):
        continue  # leave genuine ocean crossings out of overland clustering
    key = (region_of_label(r["from"]), region_of_label(r["to"]))
    if key[0] == key[1]:
        continue
    region_groups[key].append(idx)

clusters_out = []
for (reg_from, reg_to), idxs in region_groups.items():
    if len(idxs) < MIN_CLUSTER_SIZE:
        continue
    cid = len(clusters_out)
    member_routes = [routes_out[j] for j in idxs]
    total_count = sum(r["count"] for r in member_routes)
    years = [r["mean_year"] for r in member_routes]
    # average endpoint across all members, in whichever coordinate system
    # their curve exposes (bow: x1/y1/x2/y2; path/corridor: coords[0]/coords[-1])
    def ep(r):
        c = r["curve"]
        return (c["coords"][0], c["coords"][-1]) if c["mode"]=="path" else ([c["x1"],c["y1"]], [c["x2"],c["y2"]])
    starts = [ep(r)[0] for r in member_routes]
    ends = [ep(r)[1] for r in member_routes]
    avg_start = [sum(p[0] for p in starts)/len(starts), sum(p[1] for p in starts)/len(starts)]
    avg_end = [sum(p[0] for p in ends)/len(ends), sum(p[1] for p in ends)/len(ends)]
    wps = corridor_waypoints(member_routes[0]["from"], member_routes[0]["to"])
    if wps:
        pts = [avg_start] + [[*project(wlon,wlat)] for wlon,wlat in wps] + [avg_end]
        curve = {"mode": "path", "coords": catmull_rom_spline(pts)}
    else:
        cx, cy = bow_control_point(avg_start[0], avg_start[1], avg_end[0], avg_end[1], seed=cid)
        curve = {"mode": "bow", "x1":avg_start[0], "y1":avg_start[1], "cx":cx, "cy":cy, "x2":avg_end[0], "y2":avg_end[1]}
    clusters_out.append({
        "id": f"c{cid}", "curve": curve, "count": total_count,
        "mean_year": sum(years)/len(years), "min_year": min(r["min_year"] for r in member_routes),
        "max_year": max(r["max_year"] for r in member_routes),
        "from": reg_from.title(), "to": reg_to.title(), "members": idxs,
    })
    for j in idxs:
        routes_out[j]["cluster"] = cid

with open("routes_prepared.json", "w") as f:
    json.dump(routes_out, f, separators=(',',':'))
with open("clusters_prepared.json", "w") as f:
    json.dump(clusters_out, f, separators=(',',':'))
ocean_n = sum(1 for r in routes_out if r["curve"]["mode"]=="path")
fam_n = sum(1 for r in routes_out if "family_group" in r)
clustered_n = sum(1 for r in routes_out if "cluster" in r)
print(f"Routes: {len(routes_out)} ({ocean_n} ocean-crossing, {fam_n} family-tagged, {clustered_n} in {len(clusters_out)} clusters)")

# ---- places ----
def endpoints(r):
    c = r["curve"]
    if c["mode"] == "path": return c["coords"][0], c["coords"][-1]
    return [c["x1"], c["y1"]], [c["x2"], c["y2"]]

places = {}
for r in routes_out:
    p0, p1 = endpoints(r)
    for label, coord in [(r["from"], p0), (r["to"], p1)]:
        key = (round(coord[0],1), round(coord[1],1))
        if key not in places:
            places[key] = {"label": label, "x": coord[0], "y": coord[1], "touches": 0}
        places[key]["touches"] += 1
for p in places.values():
    if p["touches"] >= 10: p["tier"] = 1
    elif p["touches"] >= 4: p["tier"] = 2
    else: p["tier"] = 3
with open("places_prepared.json", "w") as f:
    json.dump(list(places.values()), f, separators=(',',':'))
print(f"Places: {len(places)}")

# ---- per-person legs (for dynamic client-side thread assembly) ----
person_legs = {}
for i, l in enumerate(legs):
    x1, y1 = project(l["from_lon"], l["from_lat"])
    x2, y2 = project(l["to_lon"], l["to_lat"])
    ocean = is_ocean_crossing(l["from_lon"], l["to_lon"])
    entry = {"from": l["from_place"], "to": l["to_place"], "year": l["to_year"],
              "x1": x1, "y1": y1, "x2": x2, "y2": y2, "ocean": ocean}
    if ocean:
        starts_in_americas = l["from_lon"] < -25
        americas_lonlat = (l["from_lon"], l["from_lat"]) if starts_in_americas else (l["to_lon"], l["to_lat"])
        old_world_lonlat = (l["to_lon"], l["to_lat"]) if starts_in_americas else (l["from_lon"], l["from_lat"])
        wps = ocean_waypoints(*americas_lonlat, *old_world_lonlat)
        if starts_in_americas:
            wps = list(reversed(wps))
        pts = [[x1,y1]] + [[*project(wlon,wlat)] for wlon,wlat in wps] + [[x2,y2]]
        entry["waypts"] = catmull_rom_spline(pts)
    waypoints = None if ocean else corridor_waypoints(l["from_place"], l["to_place"])
    if waypoints:
        pts = [[x1,y1]]
        for wlon, wlat in waypoints:
            wx, wy = project(wlon, wlat)
            jx = ((i * 2654435761) % 200 - 100) / 100.0 * 0.6
            jy = ((i * 40503 + 7) % 200 - 100) / 100.0 * 0.6
            pts.append([round(wx+jx,2), round(wy+jy,2)])
        pts.append([x2,y2])
        entry["waypts"] = catmull_rom_spline(pts)
    elif not ocean:
        cx, cy = bow_control_point(x1, y1, x2, y2, seed=i)
        entry["cx"], entry["cy"] = cx, cy
    person_legs.setdefault(l["person_id"], []).append(entry)
with open("person_legs.json", "w") as f:
    json.dump(person_legs, f, separators=(',',':'))
print(f"Person legs: {len(person_legs)} people, {sum(len(v) for v in person_legs.values())} legs")

# ---- person graph (for dynamic target/path client-side algorithms) ----
import sys
sys.path.insert(0, PROJECT_DIR)
if "geocoder" in sys.modules: del sys.modules["geocoder"]
import geocoder

with open(_os.path.join(PROJECT_DIR, "indi.json")) as f: indi = json.load(f)
with open(_os.path.join(PROJECT_DIR, "fam.json")) as f: fam = json.load(f)
with open(_os.path.join(PROJECT_DIR, "ancestors.json")) as f: anc_data = json.load(f)

james_id = anc_data["james_id"]
direct_ancestors = set(anc_data["direct_ancestors"])
SIBLING_IDS = ["@I240014574897@", "@I240014574902@"]
relevant = direct_ancestors | {james_id} | set(SIBLING_IDS)

def parse_year(date_str):
    if not date_str: return None
    m = re.search(r'(1[3-9]\d{2}|20[0-2]\d)', date_str)
    return int(m.group(1)) if m else None

def parents_of(pid):
    out = []
    for fc in indi[pid].get("famc", []):
        f = fam.get(fc)
        if not f: continue
        for p in (f.get("husb"), f.get("wife")):
            if p and p in relevant: out.append(p)
    return out

def extract_surname(raw_name):
    m = re.search(r'/([^/]*)/', raw_name or "")
    return m.group(1).strip() if m and m.group(1).strip() else None

graph = {}
unresolved = 0
for pid in relevant:
    d = indi[pid]
    by = parse_year(d.get("birt_date"))
    bp = d.get("birt_plac")
    g = geocoder.normalize_and_geocode(bp) if bp else None
    entry = {"name": d["name"].replace("/",""), "surname": extract_surname(d["name"]), "by": by,
             "bplace": g[0] if g else (bp or None), "parents": parents_of(pid)}
    if g:
        px, py = project(g[2], g[1])
        entry["bx"], entry["by_y"] = px, py
    else:
        unresolved += 1
    # fallback location for stationary-marker display (people with no legs):
    # birthplace if it resolved, otherwise try deathplace -- separate from
    # bx/by_y above, which stays strictly birthplace for target-convergence
    # accuracy (the map's whole "culminates at birth" framing)
    if g:
        entry["fx"], entry["fy"] = entry["bx"], entry["by_y"]
    else:
        dp = d.get("deat_plac")
        gd = geocoder.normalize_and_geocode(dp) if dp else None
        if gd:
            fx, fy = project(gd[2], gd[1])
            entry["fx"], entry["fy"] = fx, fy
            entry["fplace"] = gd[0]
    graph[pid] = entry

with open("person_graph.json", "w") as f:
    json.dump({"james_id": james_id, "sibling_ids": SIBLING_IDS, "people": graph}, f, separators=(',',':'))
print(f"Graph: {len(graph)} people, {unresolved} unresolved birthplaces")

# ---- search index: EVERY relevant person, not just those with legs ----
# A large fraction of direct ancestors (roughly half, in this family) lived
# their entire recorded life in one place -- multiple dated records, but
# zero actual MOVES between different places -- so they produced zero legs
# and were previously invisible to search entirely, despite being fully
# confirmed, real ancestors. Now: everyone is findable; people with no
# movement data get a "has_moves: false" flag so the client can fall back
# to a stationary point-marker (if a location is known) or an honest
# no-location note (if not), instead of silently doing nothing.
search_index = []
for pid, g in graph.items():
    entry = {"id": pid, "name": g["name"], "birt": ""}
    if g.get("by"):
        entry["birt"] = str(g["by"])
    entry["has_moves"] = pid in person_legs
    entry["has_place"] = g.get("fx") is not None
    search_index.append(entry)
search_index.sort(key=lambda e: e["name"])
with open("search_index.json", "w") as f:
    json.dump(search_index, f, separators=(',',':'))
findable_before = sum(1 for e in search_index if e["has_moves"])
print(f"Search index: {len(search_index)} people ({findable_before} with movement data, "
      f"{sum(1 for e in search_index if not e['has_moves'] and e['has_place'])} stationary-only, "
      f"{sum(1 for e in search_index if not e['has_moves'] and not e['has_place'])} with no location at all)")
