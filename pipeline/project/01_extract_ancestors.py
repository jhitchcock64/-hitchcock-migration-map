import os as _os
_ORIG_CWD = _os.getcwd()
PROJECT_DIR = _os.path.dirname(_os.path.abspath(__file__))
BUILD_DIR = _os.path.join(_os.path.dirname(PROJECT_DIR), "build2")
_os.chdir(PROJECT_DIR)  # scripts read/write their own folder regardless of where they're launched from
"""
Stage 1: Parse GEDCOM, identify James Albert Hitchcock (b. 1992),
extract every direct ancestor (and only direct ancestors), print verification output.
"""
import json
import re
from collections import deque

def _has_given(n): return bool(n) and bool(re.sub(r"/[^/]*/", "", n).strip())
GEDCOM_PATH = _os.path.join(_ORIG_CWD, _os.environ["GEDCOM"]) if _os.environ.get("GEDCOM") else None
if not GEDCOM_PATH or not _os.path.exists(GEDCOM_PATH):
    raise SystemExit("Set GEDCOM=/path/to/export.ged before running (see CLAUDE.md / pipeline/RUNBOOK.md)")

# ---------------------------------------------------------------------------
# 1. Parse the GEDCOM into indi{} and fam{} dictionaries
# ---------------------------------------------------------------------------
indi = {}   # id -> dict(name, sex, birt_date, birt_plac, deat_date, deat_plac, famc[], fams[])
fam = {}    # id -> dict(husb, wife, chil[])

cur_id = None
cur_type = None
cur_tag_ctx = None  # tracks whether we're inside BIRT/DEAT block for level-2 DATE/PLAC

with open(GEDCOM_PATH, encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.rstrip("\n")
        parts = line.split(" ", 2)
        if len(parts) < 2:
            continue
        level = parts[0]

        if level == "0":
            if len(parts) >= 3 and parts[2] == "INDI":
                cur_type = "INDI"
                cur_id = parts[1]
                indi[cur_id] = {
                    "name": None, "sex": None,
                    "birt_date": None, "birt_plac": None,
                    "deat_date": None, "deat_plac": None,
                    "famc": [], "fams": [],
                }
            elif len(parts) >= 3 and parts[2] == "FAM":
                cur_type = "FAM"
                cur_id = parts[1]
                fam[cur_id] = {"husb": None, "wife": None, "chil": []}
            else:
                cur_type = None
                cur_id = None
            cur_tag_ctx = None

        elif cur_type == "INDI" and level == "1":
            tag = parts[1]
            val = parts[2] if len(parts) > 2 else ""
            cur_tag_ctx = tag
            d = indi[cur_id]
            if tag == "NAME":
                if not (_has_given(d["name"]) and not _has_given(val)):  # a blank duplicate NAME must not overwrite a real one (v15)
                    d["name"] = val
            elif tag == "SEX":
                d["sex"] = val
            elif tag == "FAMC":
                d["famc"].append(val)
            elif tag == "FAMS":
                d["fams"].append(val)

        elif cur_type == "INDI" and level == "2":
            tag = parts[1]
            val = parts[2] if len(parts) > 2 else ""
            d = indi[cur_id]
            if tag == "DATE":
                if cur_tag_ctx == "BIRT" and d["birt_date"] is None:
                    d["birt_date"] = val
                elif cur_tag_ctx == "DEAT" and d["deat_date"] is None:
                    d["deat_date"] = val
            elif tag == "PLAC":
                if cur_tag_ctx == "BIRT" and d["birt_plac"] is None:
                    d["birt_plac"] = val
                elif cur_tag_ctx == "DEAT" and d["deat_plac"] is None:
                    d["deat_plac"] = val

        elif cur_type == "FAM" and level == "1":
            tag = parts[1]
            val = parts[2] if len(parts) > 2 else ""
            d = fam[cur_id]
            if tag == "HUSB":
                d["husb"] = val
            elif tag == "WIFE":
                d["wife"] = val
            elif tag == "CHIL":
                d["chil"].append(val)

print(f"Parsed {len(indi):,} individuals and {len(fam):,} families from GEDCOM.")

# ---------------------------------------------------------------------------
# 2. Identify James Albert Hitchcock (born 1992)
# ---------------------------------------------------------------------------
candidates = []
for pid, d in indi.items():
    name = d["name"] or ""
    if "James Albert" in name and "Hitchcock" in name:
        birth_year = None
        if d["birt_date"]:
            m = re.search(r"(1[5-9]\d{2}|20[0-2]\d)", d["birt_date"])
            if m:
                birth_year = int(m.group(1))
        candidates.append((pid, name, birth_year, d["birt_date"], d["birt_plac"]))

print(f"\nCandidates matching 'James Albert ... Hitchcock': {len(candidates)}")
for c in candidates:
    print(f"   {c}")

james_candidates_1992 = [c for c in candidates if c[2] == 1992]
if len(james_candidates_1992) != 1:
    raise SystemExit(f"Expected exactly 1 match born 1992, found {len(james_candidates_1992)}. Aborting.")

JAMES_ID = james_candidates_1992[0][0]
print(f"\n>>> Identified target individual: {indi[JAMES_ID]['name']}  "
      f"(ID {JAMES_ID}), born {indi[JAMES_ID]['birt_date']} in {indi[JAMES_ID]['birt_plac']}")

# ---------------------------------------------------------------------------
# 2b. Ad hoc addition per explicit user request: hypothetical child Margaret
#     Jean Hitchcock (b. Dec 2026, Alexandria VA), daughter of James and his
#     actual real wife Jennie Anne Askew (already in the GEDCOM with her own
#     complete ancestor chain via famc). Margaret becomes the new BFS root,
#     so extraction naturally unifies James's ~910 ancestors AND Jennie's
#     ~236 into one set -- the BFS mechanism below is already fully generic
#     and needs no modification, just a different starting point.
MARGARET_ID = "@SYNTHETIC_MARGARET_JEAN_HITCHCOCK@"
# Family IDs shift on every GEDCOM export (individual IDs don't), so find
# James+Jennie's marriage record by its two spouses. Override with the
# JAMES_JENNIE_FAM_ID environment variable only if detection ever fails.
_JAMES, _JENNIE = "@I240014574891@", "@I242606531603@"
_jj = [fid for fid, f in fam.items() if _JAMES in (f["husb"], f["wife"]) and _JENNIE in (f["husb"], f["wife"])]
JAMES_JENNIE_FAM_ID = _os.environ.get("JAMES_JENNIE_FAM_ID") or (_jj[0] if len(_jj) == 1 else None)
if not JAMES_JENNIE_FAM_ID:
    raise SystemExit(f"Could not identify a unique James+Jennie family record (found {_jj}); set JAMES_JENNIE_FAM_ID")
print(f"James+Jennie family record: {JAMES_JENNIE_FAM_ID}")
indi[MARGARET_ID] = {
    "name": "Margaret Jean /Hitchcock/", "sex": "F",
    "birt_date": "Dec 2026", "birt_plac": "Alexandria, Virginia, USA",
    "deat_date": None, "deat_plac": None,
    "famc": [JAMES_JENNIE_FAM_ID], "fams": [],
}
if JAMES_JENNIE_FAM_ID in fam and MARGARET_ID not in fam[JAMES_JENNIE_FAM_ID]["chil"]:
    fam[JAMES_JENNIE_FAM_ID]["chil"].append(MARGARET_ID)
    print(f"Injected synthetic person: Margaret Jean Hitchcock ({MARGARET_ID}), ad hoc per user request")
else:
    raise SystemExit(f"Expected family {JAMES_JENNIE_FAM_ID} to exist for James+Jennie -- aborting, ID may have changed.")

ROOT_ID = MARGARET_ID  # everything downstream roots from Margaret now, not James directly

# ---------------------------------------------------------------------------
# 3. Extract every direct ancestor (and only direct ancestors) of James
#    Direct ancestor = reachable via repeated FAMC -> {HUSB, WIFE} traversal.
#    James himself is EXCLUDED from the ancestor set/count.
# ---------------------------------------------------------------------------
visited = set()
generation_of = {}
parent_links = []  # (child_id, parent_id) edges actually used, for sanity/debug

def bfs_ancestors(root_id):
    """BFS up the tree from root_id. root_id itself is depth 0 but excluded
    from the returned ancestor set (only depth >= 1 counts as 'ancestor')."""
    visited.add(root_id)
    generation_of[root_id] = 0
    q = deque([root_id])
    while q:
        pid = q.popleft()
        depth = generation_of[pid]
        person = indi.get(pid)
        if not person:
            continue
        for famc_id in person["famc"]:
            f = fam.get(famc_id)
            if not f:
                continue
            for parent_id in (f["husb"], f["wife"]):
                if parent_id and parent_id in indi and parent_id not in visited:
                    visited.add(parent_id)
                    generation_of[parent_id] = depth + 1
                    parent_links.append((pid, parent_id))
                    q.append(parent_id)

bfs_ancestors(ROOT_ID)

direct_ancestors = [pid for pid in visited if pid != ROOT_ID]

print(f"\n{'='*70}")
print(f"DIRECT ANCESTORS FOUND: {len(direct_ancestors):,}")
print(f"{'='*70}")

max_gen = max(generation_of[p] for p in direct_ancestors)
print(f"Generations deep (parents=1 ... furthest={max_gen}):")
from collections import Counter
gen_counts = Counter(generation_of[p] for p in direct_ancestors)
for g in sorted(gen_counts):
    print(f"   gen {g:2d}: {gen_counts[g]:3d} ancestors")

# ---------------------------------------------------------------------------
# 4. List first 25 ancestors (generation order, i.e. BFS order = parents first,
#    then grandparents, etc.) with birth years, for verification
# ---------------------------------------------------------------------------
def birth_year_of(pid):
    bd = indi[pid]["birt_date"]
    if not bd:
        return None
    m = re.search(r"(1[3-9]\d{2}|20[0-2]\d)", bd)
    return int(m.group(1)) if m else None

ordered = sorted(direct_ancestors, key=lambda pid: (generation_of[pid], pid))

print(f"\nFirst 25 direct ancestors (generation order, closest first):")
print(f"{'#':<4}{'Gen':<5}{'Name':<38}{'Birth Year':<12}{'ID'}")
for i, pid in enumerate(ordered[:25], 1):
    name = (indi[pid]["name"] or "?").replace("/", "")
    by = birth_year_of(pid)
    print(f"{i:<4}{generation_of[pid]:<5}{name:<38}{str(by) if by else '?':<12}{pid}")

# ---------------------------------------------------------------------------
# Save state for next stages
# ---------------------------------------------------------------------------
with open(_os.path.join(PROJECT_DIR, "indi.json"), "w", encoding="utf-8") as f:
    json.dump(indi, f, ensure_ascii=False)
with open(_os.path.join(PROJECT_DIR, "fam.json"), "w", encoding="utf-8") as f:
    json.dump(fam, f, ensure_ascii=False)
with open(_os.path.join(PROJECT_DIR, "ancestors.json"), "w", encoding="utf-8") as f:
    json.dump({
        "james_id": ROOT_ID,  # kept as "james_id" for downstream compatibility -- now holds Margaret's ID, the new root
        "true_james_id": JAMES_ID,  # James himself, for anything that specifically needs him rather than the root
        "direct_ancestors": direct_ancestors,
        "generation_of": generation_of,
    }, f, ensure_ascii=False)

print(f"\nSaved indi.json, fam.json, ancestors.json for next stage.")
