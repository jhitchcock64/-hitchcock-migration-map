"""
The extended set of people (2026-10-02, James): everyone needed for a cousin to view their own map and
tree. Cousins are the descendants of the root's 3rd great-grandparents (generation EXT_GENERATION);
the set is those descendants plus all their ancestors (their other lines, as far as the tree has them).

The core map (data.js) stays the root's direct ancestors. The extended run of the pipeline
(HM_EXT=1, run_extended.sh) builds the same arrays over core + extended -> data_ext.js, which a page
loads instead of data.js only when the "Viewing as" person is outside the core.
"""
from collections import defaultdict

EXT_GENERATION = 5          # 3rd great-grandparents of the root


def extended(indi, fam, generation_of):
    """generation_of: {pid: generations above the root} for the core (root = 0).
    Returns (ids not in the core, generation for each): a descendant sits one below its parent,
    a married-in ancestor one above its child, so the root's own generation is 0 throughout."""
    parents = lambda i: [p for f in indi.get(i, {}).get("famc", []) if f in fam
                         for p in (fam[f].get("husb"), fam[f].get("wife")) if p and p in indi]
    kids = defaultdict(list)
    for f in fam.values():
        for p in (f.get("husb"), f.get("wife")):
            if p: kids[p] += [c for c in f.get("chil", []) if c in indi]
    gen = dict(generation_of)
    # down from the generation's ancestors
    frontier = sorted(i for i, g in generation_of.items() if g == EXT_GENERATION)
    desc = set()
    while frontier:
        nxt = []
        for x in frontier:
            for c in kids.get(x, []):
                if c not in desc:
                    desc.add(c); nxt.append(c)
                    gen.setdefault(c, gen[x] - 1)
        frontier = sorted(nxt)
    # up from every descendant
    frontier = sorted(desc); seen = set(desc)
    while frontier:
        nxt = []
        for x in frontier:
            for p in parents(x):
                if p not in seen:
                    seen.add(p); nxt.append(p)
                    gen.setdefault(p, gen[x] + 1)
        frontier = sorted(nxt)
    new = sorted(seen - set(generation_of))
    return new, {i: gen[i] for i in new}
