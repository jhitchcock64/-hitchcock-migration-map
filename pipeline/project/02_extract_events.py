import os as _os
_ORIG_CWD = _os.getcwd()
PROJECT_DIR = _os.path.dirname(_os.path.abspath(__file__))
BUILD_DIR = _os.path.join(_os.path.dirname(PROJECT_DIR), "build2")
_os.chdir(PROJECT_DIR)  # scripts read/write their own folder regardless of where they're launched from
import re
"""
Stage 2a: Pull every BIRT / DEAT / RESI event (date + place) for each of the
768 direct ancestors identified in stage 1.
"""
import json

with open(_os.path.join(PROJECT_DIR, "ancestors.json")) as f:
    anc_data = json.load(f)

SIBLING_IDS = ["@I240014574897@", "@I240014574902@"]  # Alexandra, Katherine
target_ids = set(anc_data["direct_ancestors"]) | {anc_data["james_id"]} | set(SIBLING_IDS)
print(f"Extracting event data for {len(target_ids)} people (768 ancestors + James).")

def _has_given(n): return bool(n) and bool(re.sub(r"/[^/]*/", "", n).strip())
GEDCOM_PATH = _os.path.join(_ORIG_CWD, _os.environ["GEDCOM"]) if _os.environ.get("GEDCOM") else None
if not GEDCOM_PATH or not _os.path.exists(GEDCOM_PATH):
    raise SystemExit("Set GEDCOM=/path/to/export.ged before running (see CLAUDE.md / pipeline/RUNBOOK.md)")

records = {}
MARGARET_ID = anc_data["james_id"]  # the new root -- "james_id" kept as key name for downstream compatibility
records[MARGARET_ID] = {
    "name": "Margaret Jean Hitchcock",
    "events": [{"type": "BIRT", "date": "Dec 2026", "plac": "Alexandria, Virginia, USA"}],
}
cur_id = None
cur_type = None
cur_event = None

with open(GEDCOM_PATH, encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.rstrip("\n")
        parts = line.split(" ", 2)
        if len(parts) < 2:
            continue
        level = parts[0]

        if level == "0":
            if len(parts) >= 3 and parts[2] == "INDI" and parts[1] in target_ids:
                cur_id = parts[1]
                cur_type = "INDI"
                records[cur_id] = {"name": None, "events": []}
            else:
                cur_id = None
                cur_type = None
            cur_event = None

        elif cur_type == "INDI" and level == "1":
            tag = parts[1]
            val = parts[2] if len(parts) > 2 else ""
            if tag == "NAME":
                if not (_has_given(records[cur_id]["name"]) and not _has_given(val)):  # a blank duplicate NAME must not overwrite a real one (v15)
                    records[cur_id]["name"] = val
                cur_event = None
            elif tag in ("BIRT", "DEAT", "RESI", "_MILT"):
                # _MILT: Ancestry's military service event (enlistment, a posting,
                # a campaign). Stage 3 keeps only the ones with a specific place.
                cur_event = {"type": "MILT" if tag == "_MILT" else tag, "date": None, "plac": None}
                records[cur_id]["events"].append(cur_event)
            elif tag == "EVEN":
                cur_event = {"type": "EVEN", "subtype": None, "date": None, "plac": None}
                records[cur_id]["events"].append(cur_event)
            else:
                cur_event = None

        elif cur_type == "INDI" and level == "2" and cur_event is not None:
            tag = parts[1]
            val = parts[2] if len(parts) > 2 else ""
            if tag == "DATE" and cur_event["date"] is None:
                cur_event["date"] = val
            elif tag == "PLAC" and cur_event["plac"] is None:
                cur_event["plac"] = val
            elif tag == "TYPE" and cur_event.get("type") == "EVEN":
                cur_event["subtype"] = val

missing = target_ids - set(records.keys())
print(f"People found with records: {len(records)}  |  missing: {len(missing)}")
if missing:
    print("  missing ids (unexpected):", list(missing)[:10])

# Keep only Arrival/Departure EVEN events (sourced from real passenger-list
# data -- e.g. National Archives immigration records) and normalize them to
# RESI so the rest of the pipeline treats them as ordinary presence data.
# Everything else under the generic EVEN tag (obituaries, marriage
# announcements, lawsuits, etc.) is real biographical color but not
# migration-relevant, so it's discarded here rather than polluting the map.
KEEP_EVEN_SUBTYPES = {"arrival", "departure"}
even_kept = even_dropped = 0
for r in records.values():
    kept_events = []
    for e in r["events"]:
        if e["type"] != "EVEN":
            kept_events.append(e)
            continue
        if (e.get("subtype") or "").strip().lower() in KEEP_EVEN_SUBTYPES:
            kept_events.append({"type": "RESI", "date": e["date"], "plac": e["plac"]})
            even_kept += 1
        else:
            even_dropped += 1
    r["events"] = kept_events
print(f"Arrival/Departure events kept: {even_kept}  |  other EVEN types dropped: {even_dropped}")

# --- second pass: FAM-level MARR events (date+place live on the family
# record in this GEDCOM, not the individual -- e.g. "0 @F1689@ FAM" / "1 MARR"
# / "2 DATE" / "2 PLAC"). A marriage place is genuine presence data for BOTH
# spouses and is often better-sourced than ordinary residence entries, so
# treat it as an additional RESI-equivalent event for each spouse in the set.
cur_fam_husb = cur_fam_wife = None
in_marr = False
marr_date = marr_plac = None
marr_added = 0

def flush_marriage():
    global marr_added
    if marr_plac and (cur_fam_husb in records or cur_fam_wife in records):
        for spouse in (cur_fam_husb, cur_fam_wife):
            if spouse in records:
                records[spouse]["events"].append({"type": "MARR", "date": marr_date, "plac": marr_plac})
                marr_added += 1

with open(GEDCOM_PATH, encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.rstrip("\n")
        parts = line.split(" ", 2)
        if len(parts) < 2:
            continue
        level = parts[0]

        if level == "0":
            if in_marr:
                flush_marriage()
            cur_fam_husb = cur_fam_wife = None
            in_marr = False
            marr_date = marr_plac = None
            if len(parts) >= 3 and parts[2] == "FAM":
                cur_fam_husb, cur_fam_wife = "PENDING", "PENDING"
            else:
                cur_fam_husb = cur_fam_wife = None

        elif cur_fam_husb is not None and level == "1":
            tag = parts[1]
            val = parts[2] if len(parts) > 2 else ""
            if in_marr:
                flush_marriage()
                in_marr = False
                marr_date = marr_plac = None
            if tag == "HUSB":
                cur_fam_husb = val
            elif tag == "WIFE":
                cur_fam_wife = val
            elif tag == "MARR":
                in_marr = True

        elif cur_fam_husb is not None and level == "2" and in_marr:
            tag = parts[1]
            val = parts[2] if len(parts) > 2 else ""
            if tag == "DATE" and marr_date is None:
                marr_date = val
            elif tag == "PLAC" and marr_plac is None:
                marr_plac = val
    if in_marr:
        flush_marriage()

print(f"Marriage-place events added as spouse presence data: {marr_added}")

total_events = sum(len(r["events"]) for r in records.values())
with_place = sum(1 for r in records.values() for e in r["events"] if e["plac"])
print(f"Total BIRT/DEAT/RESI events collected: {total_events}")
print(f"Events with a PLAC value: {with_place}")

# --- targeted supplemental events sourced from narrative story objects
# attached in the GEDCOM itself (OBJE records of TYPE "story"), which carry
# real biographical detail my structured BIRT/RESI/DEAT/MARR parsing can't
# reach since they're prose, not tagged fields. Added as code (persists
# across re-extraction) rather than a one-off data edit, since -- unlike
# externally-sourced additions -- this narrative genuinely lives in the
# user's own GEDCOM file; it just isn't in a form the parser reads.
WORTHINGTON_ID = "@I242209901667@"
if WORTHINGTON_ID in records:
    # "William Worthington - Biographical Data By Mrs. John Beck" (attached
    # story, @O4184@): captured 4 Jun 1781 on a George Rogers Clark
    # expedition, sold to the British at Detroit, held prisoner near
    # Montreal, escaped from an island in the St Lawrence ~40mi above
    # Montreal, returned to Westmoreland Co. PA by 20 Dec 1782 (already
    # present in the structured record as its own RESI event). Detroit added
    # per explicit user request, completing the sequence the narrative
    # already describes -- appended BEFORE Montreal so it sorts first among
    # same-year (1781) events.
    records[WORTHINGTON_ID]["events"].append(
        {"type": "RESI", "date": "1781", "plac": "Detroit, Michigan, USA"})
    records[WORTHINGTON_ID]["events"].append(
        {"type": "RESI", "date": "1781", "plac": "Montreal, Quebec, Canada"})
    print("Added William Worthington's Detroit + Montreal captivity (from attached GEDCOM narrative, Detroit ad hoc per user)")

# --- ad hoc addition per explicit user instruction (distinct provenance from
# the Worthington case above: this is the user's own stated research, not
# extracted from an attached GEDCOM document). Joseph Mitchel McDowell
# (b. abt 1785, no birthplace on record) -- his father Joseph McDowell Sr.
# died 1806 in Lewis Co., KY (formed from Mason Co. in 1806, so a residence
# there before that date is correctly "Mason Co."). Goal: give his daughter
# Abiah Frances McDowell (a direct ancestor) a unified line rather than her
# story appearing to start abruptly mid-Kentucky.
JOSEPH_MCDOWELL_ID = "@I240180933202@"
if JOSEPH_MCDOWELL_ID in records:
    for e in records[JOSEPH_MCDOWELL_ID]["events"]:
        if e["type"] == "BIRT":
            e["plac"] = "Allegheny County, Pennsylvania, USA"
            break
    records[JOSEPH_MCDOWELL_ID]["events"].append(
        {"type": "RESI", "date": "1800", "plac": "Mason County, Kentucky, USA"})
    print("Added Joseph Mitchel McDowell's birthplace and father-residence (ad hoc, per user)")

# --- ad hoc addition per explicit user instruction: Holden, Massachusetts
# residence (2002-2005), between the family's Macon, GA and Evansville, IN
# periods. James and Jean already have this correctly in their own GEDCOM
# records; Albert David, Alexandra, and Katherine are missing it. User has
# stated they will also correct the source GEDCOM directly.
HOLDEN_IDS = ["@I240014481744@", "@I240014574897@", "@I240014574902@"]  # Albert David, Alexandra, Katherine
holden_added = 0
for pid in HOLDEN_IDS:
    if pid in records:
        records[pid]["events"].append(
            {"type": "RESI", "date": "2002-2005", "plac": "Holden, Massachusetts, USA"})
        holden_added += 1
print(f"Added Holden, MA residence for {holden_added} family members (ad hoc, per user, pending GEDCOM correction)")

# --- correction per explicit user instruction: Matilda "Money" Clementine
# Roberts never spent time in Ohio -- a genuine error in the source data
# (user has already corrected this in their own records). Removing the
# 1900 Cleveland, Ohio entry persistently at the code level.
MATILDA_ROBERTS_ID = "@I242611468645@"
if MATILDA_ROBERTS_ID in records:
    before = len(records[MATILDA_ROBERTS_ID]["events"])
    records[MATILDA_ROBERTS_ID]["events"] = [
        e for e in records[MATILDA_ROBERTS_ID]["events"]
        if not (e["plac"] and "ohio" in e["plac"].lower())
    ]
    removed = before - len(records[MATILDA_ROBERTS_ID]["events"])
    print(f"Removed {removed} Ohio event(s) from Matilda Roberts's record (user-confirmed error)")

# --- correction per explicit user instruction: Thomas Robertson (d. Abt.
# 1811, Maryland) has a birthplace (Aberdeen, Scotland) but no birth date,
# so that event was being silently excluded from stop-building (a stop
# needs both a date AND a place), leaving no "Aberdeen" endpoint for his
# migration to anchor to. Adding an estimated birth year per user's own
# proposal, consistent with his death year.
THOMAS_ROBERTSON_ABERDEEN_ID = "@I242261004267@"
if THOMAS_ROBERTSON_ABERDEEN_ID in records:
    fixed = False
    for e in records[THOMAS_ROBERTSON_ABERDEEN_ID]["events"]:
        if e["type"] == "BIRT" and not e["date"]:
            e["date"] = "Abt. 1745"
            fixed = True
    print(f"Added Thomas Robertson's estimated birth year, Abt. 1745 (user-proposed): {fixed}")

# --- correction per explicit user instruction: Charles Albert Trinder's
# Halifax, Nova Scotia record (dated 1894, decades after he's already shown
# living in Ontario since 1868) is confusing/inconsistent with the family's
# actual story -- removing it entirely per user request.
CHARLES_TRINDER_ID = "@I240014571904@"
if CHARLES_TRINDER_ID in records:
    before = len(records[CHARLES_TRINDER_ID]["events"])
    records[CHARLES_TRINDER_ID]["events"] = [
        e for e in records[CHARLES_TRINDER_ID]["events"]
        if not (e["plac"] and "halifax" in e["plac"].lower())
    ]
    removed = before - len(records[CHARLES_TRINDER_ID]["events"])
    print(f"Removed {removed} Halifax event(s) from Charles Albert Trinder's record (user-confirmed)")

# --- correction per explicit user instruction: Alvis Loree Shiflet's single
# Orlando, Florida record (1952) is a data error -- an isolated outlier
# amid an otherwise entirely Virginia-based life. Removing entirely.
ALVIS_SHIFLET_ID = "@I242611525597@"
if ALVIS_SHIFLET_ID in records:
    before = len(records[ALVIS_SHIFLET_ID]["events"])
    records[ALVIS_SHIFLET_ID]["events"] = [
        e for e in records[ALVIS_SHIFLET_ID]["events"]
        if not (e["plac"] and "orlando" in e["plac"].lower())
    ]
    removed = before - len(records[ALVIS_SHIFLET_ID]["events"])
    print(f"Removed {removed} Orlando, FL event(s) from Alvis Loree Shiflet's record (user-confirmed error)")

# --- correction per explicit user instruction: George Watts's single "New
# York, United States" record (1 Jul 1863) is a data error -- an isolated
# outlier amid an otherwise entirely Washington, Warren Co., NJ life.
GEORGE_WATTS_ID = "@I240016223823@"
if GEORGE_WATTS_ID in records:
    before = len(records[GEORGE_WATTS_ID]["events"])
    records[GEORGE_WATTS_ID]["events"] = [
        e for e in records[GEORGE_WATTS_ID]["events"]
        if not (e["plac"] and e["plac"].strip().lower().startswith("new york"))
    ]
    removed = before - len(records[GEORGE_WATTS_ID]["events"])
    print(f"Removed {removed} New York event(s) from George Watts's record (user-confirmed error)")

# --- correction per explicit user instruction: Jabez Bostwick's single
# "Village of Buffalo" record (1815) is a data error -- an isolated outlier
# amid an otherwise entirely Hamden/Delhi, Delaware Co., NY life.
JABEZ_BOSTWICK_ID = "@I240016443011@"
if JABEZ_BOSTWICK_ID in records:
    before = len(records[JABEZ_BOSTWICK_ID]["events"])
    records[JABEZ_BOSTWICK_ID]["events"] = [
        e for e in records[JABEZ_BOSTWICK_ID]["events"]
        if not (e["plac"] and "buffalo" in e["plac"].lower())
    ]
    removed = before - len(records[JABEZ_BOSTWICK_ID]["events"])
    print(f"Removed {removed} Buffalo event(s) from Jabez Bostwick's record (user-confirmed error)")

# --- correction per explicit user instruction: George Watts's single "New
# York, United States" record (1 Jul 1863) is a data error -- an isolated
# outlier amid an otherwise entirely Washington, Warren Co., NJ life.
GEORGE_WATTS_ID = "@I240016223823@"
if GEORGE_WATTS_ID in records:
    before = len(records[GEORGE_WATTS_ID]["events"])
    records[GEORGE_WATTS_ID]["events"] = [
        e for e in records[GEORGE_WATTS_ID]["events"]
        if not (e["plac"] and e["plac"].strip().lower().startswith("new york"))
    ]
    removed = before - len(records[GEORGE_WATTS_ID]["events"])
    print(f"Removed {removed} New York event(s) from George Watts's record (user-confirmed error)")

# --- correction per explicit user instruction: Jabez Bostwick's single
# "Village of Buffalo" record (1815) is a data error -- an isolated outlier
# amid an otherwise entirely Hamden/Delhi, Delaware Co., NY life.
JABEZ_BOSTWICK_ID = "@I240016443011@"
if JABEZ_BOSTWICK_ID in records:
    before = len(records[JABEZ_BOSTWICK_ID]["events"])
    records[JABEZ_BOSTWICK_ID]["events"] = [
        e for e in records[JABEZ_BOSTWICK_ID]["events"]
        if not (e["plac"] and "buffalo" in e["plac"].lower())
    ]
    removed = before - len(records[JABEZ_BOSTWICK_ID]["events"])
    print(f"Removed {removed} Buffalo event(s) from Jabez Bostwick's record (user-confirmed error)")

# --- correction per explicit user instruction: Jabez Bostwick's single
# "Village of Buffalo" record (1815) is a data error -- an isolated outlier
# amid an otherwise entirely Hamden/Delhi, Delaware Co., NY life. Removing
# entirely; user will correct at the source in the next GEDCOM export.
JABEZ_BOSTWICK_ID = "@I240016443011@"
if JABEZ_BOSTWICK_ID in records:
    before = len(records[JABEZ_BOSTWICK_ID]["events"])
    records[JABEZ_BOSTWICK_ID]["events"] = [
        e for e in records[JABEZ_BOSTWICK_ID]["events"]
        if not (e["plac"] and "buffalo" in e["plac"].lower())
    ]
    removed = before - len(records[JABEZ_BOSTWICK_ID]["events"])
    print(f"Removed {removed} Buffalo event(s) from Jabez Bostwick's record (user-confirmed error)")

# --- correction per explicit user instruction: George Watts's single "New
# York, United States" record (1 Jul 1863) is a data error -- an isolated
# outlier amid an otherwise entirely Washington, Warren Co., NJ life.
# Removing entirely; user has already corrected at the source.
GEORGE_WATTS_ID = "@I240016223823@"
if GEORGE_WATTS_ID in records:
    before = len(records[GEORGE_WATTS_ID]["events"])
    records[GEORGE_WATTS_ID]["events"] = [
        e for e in records[GEORGE_WATTS_ID]["events"]
        if not (e["plac"] and e["plac"].strip().lower().startswith("new york"))
    ]
    removed = before - len(records[GEORGE_WATTS_ID]["events"])
    print(f"Removed {removed} New York event(s) from George Watts's record (user-confirmed error)")

# --- targeted fix: John Mehrle (b. 1871, Baiersbronn) has a dated-but-
# placeless "1882" RESI record on his own GEDCOM entry -- a stop needs both
# a date AND a resolvable place, so it was being silently dropped, and the
# pipeline jumped straight to his next fully-dated record (1900), making it
# look like he arrived 18 years later than he actually did. His father,
# Jakob Friedrich Moehrle, has an independently sourced "20 Sep 1882, New
# York, New York, USA" record for the exact same year -- almost certainly
# the same arrival, just missing the place value on John's individual
# entry. Filling in from that specific, matching corroboration, not a guess.
JOHN_MEHRLE_ID = "@I240020560711@"
if JOHN_MEHRLE_ID in records:
    filled = False
    for e in records[JOHN_MEHRLE_ID]["events"]:
        if e["type"] == "RESI" and e["date"] == "1882" and not e["plac"]:
            e["plac"] = "New York, New York, USA"
            filled = True
            break
    print(f"Filled John Mehrle's 1882 arrival place from his father's matching record: {filled}")

# --- John Grove Speer's 1850 westward and 1857 return journey, per explicit
# user request, researched directly from his own memoir ("Reminiscences of
# the Speer Family," 1900), hosted at hyperphysics.phy-astr.gsu.edu/Nave-html.
# His existing GEDCOM record collapses this entire journey into a single
# point ("Nevada City, 1853"). Every waypoint below is a real place directly
# named in his own narrative or the site's historical research. Two dates
# are explicit in the source (departure and Panama arrival); all other
# intermediate dates are ESTIMATED from typical 1850s wagon-train/steamer
# pacing to fit between those anchors and his existing GEDCOM dates, not
# stated by Speer himself -- clearly not authoritative to the day.
JOHN_GROVE_SPEER_ID = "@I240016590471@"
SPEER_JOURNEY = [
    # --- Westward, 1850 ---
    ("2 May 1850", "Louisville, Kentucky, USA"),          # explicit: his own stated departure date
    ("10 May 1850", "St. Louis, Missouri, USA"),           # estimated: steamboat down the Ohio
    ("18 May 1850", "Lexington, Missouri, USA"),           # estimated: second steamboat up the Missouri
    ("1 Jun 1850", "Lone Jack, Missouri, USA"),            # estimated: overland to the rendezvous; waited here for grass
    ("5 Jul 1850", "Fort Kearny, Nebraska, USA"),          # estimated: ~340 mi per his own account
    ("20 Jul 1850", "Fort Laramie, Wyoming, USA"),         # estimated: ~640 mi total per his own account
    ("5 Aug 1850", "South Pass, Wyoming, USA"),            # estimated: continental divide crossing
    ("20 Aug 1850", "Soda Springs, Idaho, USA"),           # estimated: Bear River, several days camped; head of Hudspeth's Cutoff
    ("5 Sep 1850", "Humboldt River, Nevada, USA"),         # estimated: trail meets the river near Wells
    ("20 Sep 1850", "Humboldt Sink, Nevada, USA"),         # estimated: end of the ~330-mile river
    ("25 Sep 1850", "Carson River, Nevada, USA"),          # estimated: first fresh water after the 40-mile desert
    ("10 Oct 1850", "Sacramento, California, USA"),        # estimated: after the Sierra Nevada crossing
    ("15 Oct 1850", "Nevada City, California, USA"),       # estimated: his own account says two days from Sacramento
    # --- Return, 1857 ---
    ("1 Jun 1857", "Sacramento, California, USA"),         # estimated: stage from Nevada City
    ("3 Jun 1857", "San Francisco, California, USA"),      # estimated: steamboat down the Sacramento River
    ("15 Jun 1857", "Acapulco, Mexico"),                   # estimated: mail steamer stopover for water/beef
    ("24 Jun 1857", "Panama City, Panama"),                # explicit: his own account says "in June" 1857
    ("25 Jun 1857", "Colon, Panama"),                      # estimated: rail crossing of the isthmus, next day
    ("5 Jul 1857", "New York City, New York, USA"),        # estimated: mail steamer around Florida
    ("10 Jul 1857", "Cincinnati, Ohio, USA"),               # estimated: train through Pennsylvania and Ohio
    ("11 Jul 1857", "Covington, Kentucky, USA"),            # estimated: across the Ohio River
    ("12 Jul 1857", "Lexington, Kentucky, USA"),            # estimated
    ("15 Jul 1857", "Floydsburg, Oldham County, Kentucky, USA"),  # estimated: arrival home
]
if JOHN_GROVE_SPEER_ID in records:
    for date, plac in SPEER_JOURNEY:
        records[JOHN_GROVE_SPEER_ID]["events"].append({"type": "RESI", "date": date, "plac": plac})
    print(f"Added {len(SPEER_JOURNEY)} waypoints to John Grove Speer's 1850/1857 journey (per user request, from his own memoir)")

# --- John Grove Speer's 1850 westward and 1857 return journey, per explicit
# user request, researched directly from his own memoir ("Reminiscences of
# the Speer Family," 1900), hosted at hyperphysics.phy-astr.gsu.edu/Nave-html.
# His existing GEDCOM record collapses this entire journey into a single
# point ("Nevada City, 1853"). Every waypoint below is a real place directly
# named in his own narrative or the site's historical research. Two dates
# are explicit in the source (departure and Panama arrival); all other
# intermediate dates are ESTIMATED from typical 1850s wagon-train/steamer
# pacing to fit between those anchors and his existing GEDCOM dates, not
# stated by Speer himself -- clearly not authoritative to the day.
JOHN_GROVE_SPEER_ID = "@I240016590471@"

# --- John Grove Speer's 1850 westward and 1857 return journey, per explicit
# user request, researched directly from his own memoir ("Reminiscences of
# the Speer Family," 1900), hosted at hyperphysics.phy-astr.gsu.edu/Nave-html.
# His existing GEDCOM record collapses this entire journey into a single
# point ("Nevada City, 1853"). Every waypoint below is a real place directly
# named in his own narrative or the site's historical research. Two dates
# are explicit in the source (departure and Panama arrival); all other
# intermediate dates are ESTIMATED from typical 1850s wagon-train/steamer
# pacing to fit between those anchors and his existing GEDCOM dates, not
# stated by Speer himself -- clearly not authoritative to the day.
JOHN_GROVE_SPEER_ID = "@I240016590471@"

with open(_os.path.join(PROJECT_DIR, "events.json"), "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False)
print("Saved events.json")
