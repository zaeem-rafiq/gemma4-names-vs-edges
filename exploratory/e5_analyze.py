# EXPLORATORY (not pre-registered). E5 analysis: JSON-format Study A cells against the registered cells.
# Paired by (item, perm); item-cluster bootstrap (10,000 draws, seed 0). Run with python3 -I.
import os
import json, random, statistics as st, sys
P = os.environ["P"]  # the project folder (redacted in the release; was an absolute path)
X = P + "/exploratory-v1.1/"  # the author's folder layout; point it at your copy of these files
def rows(path):
    with open(path) as f:
        next(f)
        for l in f:
            r = json.loads(l)
            if "item_id" in r and "pred_letter" in r: yield r
def cells(path):
    c = {}
    for r in rows(path):
        c[(r["item_id"], r["perm"], r["version"])] = (int(r["pred_letter"] == r["correct_letter"]), r["letter_mass"])
    return c
def boot(pairs, seed=0):
    by = {}
    for (item, perm), d in pairs: by.setdefault(item, []).append(d)
    items = sorted(by); rng = random.Random(seed)
    m = st.mean(d for _, d in pairs)
    bs = []
    for _ in range(10000):
        ds = [d for it in rng.choices(items, k=len(items)) for d in by[it]]
        bs.append(st.mean(ds))
    bs.sort()
    return {"n_pairs": len(pairs), "n_items": len(items), "mean": round(m, 4), "ci95": [round(bs[249], 4), round(bs[9749], 4)]}
res = {"label": "EXPLORATORY, not pre-registered", "models": {}}
for m, vers, perms in (("31B", ("G1J", "G3J"), (1,)), ("E4B", ("G1J",), (1, 2))):
    try:
        new = cells(X + f"e5_{m}.jsonl")
    except FileNotFoundError:
        continue
    reg = cells(P + f"/studyA-v1.0/runs/studyA_{m}.jsonl")
    keys = sorted({(i, p) for (i, p, v) in new})
    o = {"n_item_perms": len(keys), "acc": {}, "letter_mass_ge_0.9": {}}
    for v, src in (("G0", reg), ("G1", reg), ("G3", reg)) + tuple((x, new) for x in vers):
        vals = [src[(i, p, v)] for i, p in keys if (i, p, v) in src]
        o["acc"][v] = round(st.mean(a for a, _ in vals), 4)
        o["letter_mass_ge_0.9"][v] = round(st.mean(int(lm >= 0.9) for _, lm in vals), 4)
    def diff(a, sa, b, sb):
        return [((i, p), sa[(i, p, a)][0] - sb[(i, p, b)][0]) for i, p in keys if (i, p, a) in sa and (i, p, b) in sb]
    o["G1J_minus_G1"] = boot(diff("G1J", new, "G1", reg))
    o["G1J_minus_G0"] = boot(diff("G1J", new, "G0", reg))
    o["G1_minus_G0_registered"] = boot(diff("G1", reg, "G0", reg))
    if "G3J" in vers:
        o["G1J_minus_G3J"] = boot(diff("G1J", new, "G3J", new))
        o["G1_minus_G3_registered"] = boot(diff("G1", reg, "G3", reg))
        o["G3J_minus_G3"] = boot(diff("G3J", new, "G3", reg))
    res["models"][m] = o
json.dump(res, open(sys.argv[1], "w"), indent=1); print(json.dumps(res, indent=1))
