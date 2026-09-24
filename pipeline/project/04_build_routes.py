import os as _os
_ORIG_CWD = _os.getcwd()
PROJECT_DIR = _os.path.dirname(_os.path.abspath(__file__))
BUILD_DIR = _os.path.join(_os.path.dirname(PROJECT_DIR), "build2")
_os.chdir(PROJECT_DIR)  # scripts read/write their own folder regardless of where they're launched from
"""
Stage 4: Bundle individual migration legs into aggregate ROUTES (same
from-place -> to-place pair, regardless of which ancestor or exact year),
compute a great-circle interpolated path for each, and write
migration_routes.geojson.
"""
import json
import math
from collections import defaultdict

with open("legs.json") as f:
    legs = json.load(f)

def great_circle_points(lat1, lon1, lat2, lon2, n=48):
    """Slerp between two points on a sphere, returning n+1 (lon,lat) points."""
    def to_vec(lat, lon):
        lat_r, lon_r = math.radians(lat), math.radians(lon)
        return (math.cos(lat_r) * math.cos(lon_r),
                math.cos(lat_r) * math.sin(lon_r),
                math.sin(lat_r))
    def to_lonlat(v):
        x, y, z = v
        lat = math.degrees(math.asin(max(-1, min(1, z))))
        lon = math.degrees(math.atan2(y, x))
        return (lon, lat)

    v1, v2 = to_vec(lat1, lon1), to_vec(lat2, lon2)
    dot = max(-1, min(1, sum(a * b for a, b in zip(v1, v2))))
    theta = math.acos(dot)
    points = []
    if theta < 1e-9:
        return [(lon1, lat1), (lon2, lat2)]
    for i in range(n + 1):
        t = i / n
        a = math.sin((1 - t) * theta) / math.sin(theta)
        b = math.sin(t * theta) / math.sin(theta)
        v = tuple(a * v1[k] + b * v2[k] for k in range(3))
        points.append(to_lonlat(v))
    return points

# --- bundle legs into directional routes, split by era where the same
# place-pair was used by clearly unrelated waves decades/centuries apart
# (e.g. "England -> Virginia" was used by immigrants across 5 different
# generations from 1624 to 1745 -- treating that as one migration event with
# one averaged color would misrepresent it; a >30yr gap between consecutive
# uses is treated as a break between distinct migration waves) ---
ERA_GAP_YEARS = 30

raw_groups = defaultdict(list)
for leg in legs:
    raw_groups[(leg["from_place"], leg["to_place"])].append(leg)

routes = {}
split_count = 0
for (frm, to), group_legs in raw_groups.items():
    group_legs.sort(key=lambda l: l["to_year"])
    clusters = [[group_legs[0]]]
    for l in group_legs[1:]:
        if l["to_year"] - clusters[-1][-1]["to_year"] > ERA_GAP_YEARS:
            clusters.append([])
        clusters[-1].append(l)
    if len(clusters) > 1:
        split_count += 1
    for i, cluster in enumerate(clusters):
        key = (frm, to) if len(clusters) == 1 else (frm, to, i)
        r = {"count": len(cluster), "years": [l["to_year"] for l in cluster],
             "people": [l["person_name"] for l in cluster],
             "from_lat": cluster[0]["from_lat"], "from_lon": cluster[0]["from_lon"],
             "to_lat": cluster[0]["to_lat"], "to_lon": cluster[0]["to_lon"]}
        routes[key] = r

print(f"Individual legs: {len(legs)}")
print(f"Bundled into {len(routes)} distinct directional routes")
print(f"Place-pairs split into multiple era-separated routes: {split_count}")

top_routes = sorted(routes.items(), key=lambda kv: -kv[1]["count"])[:15]
print("\nTop 15 busiest routes (by ancestor count using that path):")
for key, r in top_routes:
    frm, to = key[0], key[1]
    print(f"  {r['count']:3d}x  {frm:28s} -> {to:28s}  (yrs {min(r['years'])}-{max(r['years'])})")

# --- build GeoJSON ---
features = []
for key, r in routes.items():
    frm, to = key[0], key[1]
    coords = great_circle_points(r["from_lat"], r["from_lon"], r["to_lat"], r["to_lon"], n=48)
    mean_year = sum(r["years"]) / len(r["years"])
    features.append({
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[round(lo, 4), round(la, 4)] for lo, la in coords]},
        "properties": {
            "from_place": frm,
            "to_place": to,
            "ancestor_count": r["count"],
            "min_year": min(r["years"]),
            "max_year": max(r["years"]),
            "mean_year": round(mean_year, 1),
            "sample_people": sorted(set(r["people"]))[:5],
        },
    })

geojson = {"type": "FeatureCollection", "features": features}
with open("migration_routes.geojson", "w", encoding="utf-8") as f:
    json.dump(geojson, f, ensure_ascii=False)

print(f"\nWrote migration_routes.geojson  ({len(features)} LineString features)")

with open("routes.json", "w", encoding="utf-8") as f:
    json.dump({f"{k[0]}|||{k[1]}": v for k, v in routes.items()}, f, ensure_ascii=False)
print("Wrote routes.json (for map stage)")
