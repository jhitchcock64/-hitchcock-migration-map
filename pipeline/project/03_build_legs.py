import os as _os
_ORIG_CWD = _os.getcwd()
PROJECT_DIR = _os.path.dirname(_os.path.abspath(__file__))
BUILD_DIR = _os.path.join(_os.path.dirname(PROJECT_DIR), "build2")
_os.chdir(PROJECT_DIR)  # scripts read/write their own folder regardless of where they're launched from
"""
Stage 3: For every direct ancestor, order their dated events chronologically,
dedupe consecutive same-place stays, and emit one row per migration LEG
(a move from one place to the next). Writes migration_legs.csv.
"""
import json
import re
import csv
from geocoder import normalize_and_geocode

with open("events.json") as f:
    records = json.load(f)
with open("ancestors.json") as f:
    anc_data = json.load(f)

direct_ancestors = set(anc_data["direct_ancestors"])
james_id = anc_data["james_id"]
generation_of = anc_data["generation_of"]

def parse_year(datestr, birth_year=None):
    if not datestr:
        return None
    years = [int(y) for y in re.findall(r"(1[3-9]\d{2}|20[0-2]\d)", datestr)]
    if not years:
        return None
    if birth_year:
        # a string with multiple year-like numbers is usually a range (e.g.
        # "1682-1750") representing a broad lifetime estimate, not a precise
        # early date -- prefer whichever number doesn't predate birth, rather
        # than blindly taking the first, which can otherwise sort an event
        # BEFORE the person was even born and corrupt the whole sequence
        sensible = [y for y in years if y >= birth_year]
        if sensible:
            return sensible[0]
    return years[0]

MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def month_day(datestr, year):
    """Month and day of a single dated event in `year` ("4 Jun 1918" -> 6*32+4),
    for ordering stops within one year; 0 when the date gives only the year
    or is a range. (Added 2026-09-25: stops used to be ordered by year only,
    so a sailing in June and a battle in September of the same year could
    come out in either order.)"""
    if not datestr or len(re.findall(r"\d{4}", datestr)) != 1:
        return 0
    m = re.search(r"(?:(\d{1,2})\s+)?([A-Za-z]{3})[a-z]*\.?\s+" + str(year), datestr)
    if not m or m.group(2).lower() not in MONTHS:
        return 0
    return MONTHS[m.group(2).lower()] * 32 + int(m.group(1) or 0)


import math

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

SAME_PLACE_KM = 8.0  # below this, treat consecutive stops as "no real move"
                      # (handles cases like a county-level fallback landing on
                      # its own county seat, or same-metro relabeling)

# NOTE: there used to be a hardcoded CULMINATION_YEAR=1992 cutoff here,
# dropping any event after James's birth. That was correct for James
# specifically but wrong for every other possible target (e.g. Katherine,
# born 1997 -- it silently deleted her parents' 1996 move to Macon, GA,
# which is BEFORE her own birth but after James's). "The story ends at the
# target's birth" is a per-target rule, not a fixed year, so it now lives
# client-side, scoped to just the target's own parents, not a blanket cutoff
# applied to every person in the tree regardless of who's being viewed.

# rough bounding boxes for country-tier redundancy detection -- only the
# countries that actually appear as documented origins in this family's data
COUNTRY_BBOX = {
    "germany": (47.2, 55.1, 5.8, 15.1),
    "england": (49.9, 55.8, -6.5, 1.8),
    "wales": (51.3, 53.5, -5.5, -2.6),
    "scotland": (54.6, 60.9, -8.7, -0.7),
    "ireland": (51.4, 55.4, -10.6, -5.3),
    "sweden": (55.3, 69.1, 10.9, 24.2),
    "switzerland": (45.8, 47.9, 5.9, 10.6),
    "netherlands": (50.7, 53.6, 3.3, 7.3),
    "canada": (41.7, 83.1, -141.0, -52.6),
}

def region_of_label(label):
    """'Caroline Co., Virginia' -> 'virginia'. None if label has no comma
    (i.e. is itself already just a bare region/country name)."""
    if "," not in label:
        return None
    return label.rsplit(",", 1)[-1].strip().lower()

def strip_generic_singletons(evs):
    """Drop a lone region- or country-tier event when this same person has
    OTHER, more specific events covering that same broader area. A bare
    'Virginia' sitting next to several 'Caroline Co., Virginia' records adds
    no real information -- it's almost always a less-precisely-transcribed
    version of the same residence, not a genuine separate move -- and left
    in, it can fabricate a fake back-and-forth in the migration timeline."""
    specific_regions = {region_of_label(e["label"]) for e in evs if e["tier"] in ("town", "county")}
    specific_regions.discard(None)
    out = []
    for e in evs:
        if e["tier"] == "region" and e["label"].lower() in specific_regions:
            continue
        if e["tier"] == "country":
            bbox = COUNTRY_BBOX.get(e["label"].lower())
            if bbox:
                lat_min, lat_max, lon_min, lon_max = bbox
                if any(o is not e and o["tier"] in ("town", "county", "region") and
                       lat_min <= o["lat"] <= lat_max and lon_min <= o["lon"] <= lon_max
                       for o in evs):
                    continue
        out.append(e)
    return out

def person_stops(pid):
    r = records[pid]
    birth_year = None
    for e in r["events"]:
        if e["type"] == "BIRT":
            y = parse_year(e["date"])
            if y:
                birth_year = y
                break
    evs = []
    seen_types = set()
    for e in r["events"]:
        # MARR: the marriage place (from the family record, added to both spouses in
        # stage 2) is presence data like a residence. It was extracted but dropped
        # here until 2026-09-25, so no marriage place ever reached the map.
        if e["type"] not in ("BIRT", "RESI", "DEAT", "MILT", "MARR"):
            continue
        if e["type"] in ("BIRT", "DEAT") and e["type"] in seen_types:
            continue  # keep only first birth/death record (dedupe source variants)
        g = normalize_and_geocode(e["plac"])
        if not g:
            continue
        label, lat, lon, tier = g
        if e["type"] == "MILT" and tier not in ("town", "county"):
            continue  # "Virginia, USA" says where he enlisted or served, not a place he went
        if e["type"] == "MARR" and tier not in ("town", "county"):
            continue  # a marriage "in New England" or "Virginia" is no place to draw a trip to
        yr = parse_year(e["date"], birth_year)
        if yr and birth_year and not (birth_year - 5 <= yr <= birth_year + 100):
            continue  # discard implausible/garbled date ranges
        if yr is None:
            continue
        evs.append({"label": label, "lat": lat, "lon": lon, "tier": tier,
                     "year": yr, "type": e["type"], "md": month_day(e["date"], yr)})
        if e["type"] in ("BIRT", "DEAT"):
            seen_types.add(e["type"])
    evs = strip_generic_singletons(evs)
    evs = drop_home_military(evs)
    evs.sort(key=lambda e: (e["year"], 0 if e["type"] == "BIRT" else (2 if e["type"] == "DEAT" else 1), e["md"]))
    stops = []
    for e in evs:
        if stops and haversine_km(stops[-1]["lat"], stops[-1]["lon"], e["lat"], e["lon"]) < SAME_PLACE_KM:
            continue
        stops.append(e)
    return collapse_side_trips(stops)

MILT_AWAY_KM = 60


def drop_home_military(evs):
    """A military record at (or near) where the person was living anyway --
    enlisting at home, a pension filed at home -- adds no journey, only a
    spurious hop. Keep a military stop only if it's at least MILT_AWAY_KM from
    the person's stops on either side of it in time."""
    order = sorted(evs, key=lambda e: (e["year"], 0 if e["type"] == "BIRT" else (2 if e["type"] == "DEAT" else 1), e["md"]))
    out = []
    for i, e in enumerate(order):
        if e["type"] == "MILT":
            near = [o for o in (order[i - 1] if i > 0 else None, order[i + 1] if i + 1 < len(order) else None)
                    if o is not None and o["type"] != "MILT"]
            if any(haversine_km(o["lat"], o["lon"], e["lat"], e["lon"]) < MILT_AWAY_KM for o in near):
                continue
        out.append(e)
    return out


def collapse_side_trips(stops, max_gap_years=5):
    """Trim BRIEF out-and-back detours: A -> B -> A where the whole round trip
    took a few years or less. Deliberately time-gated, not just shape-gated --
    an early version collapsed ANY exact A-B-A pattern regardless of how long
    the person was away, which wrongly erased John Grove Speer's Kentucky ->
    Nevada City, California -> Kentucky trip (1847-1858, a real ~decade-long
    Gold Rush sojourn) using the same logic meant for a mere 1-year detour."""
    out = []
    i = 0
    while i < len(stops):
        if (i + 2 < len(stops) and stops[i+1]["type"] != "MILT" and   # a campaign away and back is the point
                haversine_km(stops[i]["lat"], stops[i]["lon"], stops[i+2]["lat"], stops[i+2]["lon"]) < SAME_PLACE_KM and
                (stops[i+2]["year"] - stops[i]["year"]) <= max_gap_years):
            merged = dict(stops[i])
            merged["year"] = stops[i+2]["year"]  # keep the later date -- when they actually moved on
            out.append(merged)
            i += 3  # skip the collapsed detour (i+1) and its closing revisit (i+2)
        else:
            out.append(stops[i])
            i += 1
    return out

legs = []
people_with_no_dated_places = 0
people_with_single_stop = 0

SIBLING_IDS = ["@I240014574897@", "@I240014574902@"]  # Alexandra, Katherine
JAMES_ID = anc_data["james_id"]
for extra in [JAMES_ID] + SIBLING_IDS:
    generation_of.setdefault(extra, 0)  # same tier as the root -- not an "ancestor" of anyone

for pid in sorted(set(direct_ancestors) | {JAMES_ID} | set(SIBLING_IDS), key=lambda p: generation_of[p]):
    name = (records[pid]["name"] or "?").replace("/", "")
    stops = person_stops(pid)
    if not stops:
        people_with_no_dated_places += 1
        continue
    if len(stops) == 1:
        people_with_single_stop += 1
        continue
    for i in range(len(stops) - 1):
        a, b = stops[i], stops[i + 1]
        legs.append({
            "person_id": pid,
            "person_name": name,
            "generation": generation_of[pid],
            "leg_order": i + 1,
            "from_place": a["label"], "from_lat": a["lat"], "from_lon": a["lon"], "from_tier": a["tier"],
            "to_place": b["label"], "to_lat": b["lat"], "to_lon": b["lon"], "to_tier": b["tier"],
            "from_year": a["year"], "to_year": b["year"], "event_type": b["type"],
        })

print(f"Direct ancestors processed: {len(direct_ancestors)}")
print(f"  - with no resolvable dated place at all: {people_with_no_dated_places}")
print(f"  - with only a single stop (no internal move): {people_with_single_stop}")
print(f"  - contributing >=1 migration leg: {len(direct_ancestors) - people_with_no_dated_places - people_with_single_stop}")
print(f"\nTotal migration legs: {len(legs)}")

fieldnames = ["person_id","person_name","generation","leg_order",
              "from_place","from_lat","from_lon","from_tier",
              "to_place","to_lat","to_lon","to_tier",
              "from_year","to_year","event_type"]

with open("migration_legs.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(legs)

print("Wrote migration_legs.csv")

with open("legs.json", "w", encoding="utf-8") as f:
    json.dump(legs, f, ensure_ascii=False)
print("Wrote legs.json (for next stage)")

# quick sanity peek
print("\nFirst 8 legs:")
for l in legs[:8]:
    print(f"  {l['person_name']:30s} {l['from_place']:28s} -> {l['to_place']:28s}  ({l['to_year']})")
