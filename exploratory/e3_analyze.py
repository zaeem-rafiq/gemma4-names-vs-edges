# EXPLORATORY (not pre-registered). E3 analysis: Acc@1 per model and cell, paired contrasts with task-bootstrap CIs,
# the gain from the hint against the matching Study B cells without the hint, and the "pick uniformly among the
# hinted neighbours" baseline from the shown blocks. Run with python3 -I.
import os
import json, random, statistics as st, sys
P = os.environ["P"]  # the project folder (redacted in the release; was an absolute path)
X = P + "/exploratory-v1.1/"  # the author's folder layout; point it at your copy of these files
T = json.load(open(X + "e3_tasks.json"))["tasks"]; ids = {t["task_id"]: t for t in T}
FZ = {}
for s in ("official", "lite"):
    for t in json.load(open(f"{P}/studyb-frozen/{s}/tasks.json"))["tasks"]:
        if t["task_id"] in ids: FZ[t["task_id"]] = t
def boot(d, seed=0):
    if not d: return None
    rng = random.Random(seed); n = len(d)
    b = sorted(st.mean(rng.choices(d, k=n)) for _ in range(10000))
    return {"n": n, "mean": round(st.mean(d), 4), "ci95": [round(b[249], 4), round(b[9749], 4)]}
def load(path, naming):
    acc = {}
    for l in open(path).read().splitlines()[1:]:
        r = json.loads(l)
        if "item_id" not in r or r["item_id"] not in ids or r.get("naming", naming) != naming: continue
        acc.setdefault(r["item_id"], {})[(r["graph"], r["perm"])] = int(r["pred_letter"] in r["correct_letters"])
    return acc
def per_task(acc, g):
    return {t: st.mean(v[(g, o)] for o in (1, 2)) for t, v in acc.items() if all((g, o) in v for o in (1, 2))}
res = {"label": "EXPLORATORY, not pre-registered", "n_tasks": len(T), "models": {}}
SB = {"E4B": [P + "/studyB-v1.1/runs/studyB_official_E4B.jsonl", P + "/studyB-v1.1/runs/studyB_lite_E4B.jsonl"],
      "31B": [P + "/studyB-v1.1/runs/studyB_official_31B.jsonl", P + "/studyB-v1.1/runs/studyB_lite_31B.jsonl"]}
for m in ("E4B", "31B"):
    try:
        h = load(X + f"e3_{m}.jsonl", "opaque_hint")
    except FileNotFoundError:
        continue
    nh = {}
    for f in SB[m]:
        for k, v in load(f, "opaque").items(): nh.setdefault(k, {}).update(v)
    o = {"acc_hint": {}, "acc_nohint_studyB": {}}
    for g in ("true", "rewired", "none"):
        a, b = per_task(h, g), per_task(nh, g)
        o["acc_hint"][g] = round(st.mean(a.values()), 4) if a else None
        o["acc_nohint_studyB"][g] = round(st.mean(b.values()), 4) if b else None
        o[f"hint_gain_{g}"] = boot([a[t] - b[t] for t in a if t in b])
    at, ar, an = per_task(h, "true"), per_task(h, "rewired"), per_task(h, "none")
    o["hint_true_minus_rewired"] = boot([at[t] - ar[t] for t in at if t in ar])
    o["hint_true_minus_none"] = boot([at[t] - an[t] for t in at if t in an])
    o["n_tasks_scored"] = len(at)
    o["note"] = "31B on Lite is descriptive in Study B; its no-hint cells come from studyB_lite_31B.jsonl" if m == "31B" else ""
    res["models"][m] = o
# (a) hinted-neighbour baseline from the shown blocks (frozen contexts; same block in both orders)
base = {}
for arm in ("true", "rewired"):
    ks, inv, hit = [], [], 0
    for tid, t in ids.items():
        rec = FZ[tid]; ctx = rec["context"][arm]; a0 = t["first_anchor"]
        edges = [tuple(e) for e in ctx["subgraph"]["edges"]]
        if "neighbors" in ctx and ctx["neighbors"]["node"] == a0:
            edges += [(a0, y) for y in ctx["neighbors"]["neighbors"]]
        nbr = {b for x, b in edges if x == a0} | {x for x, b in edges if b == a0}
        cand = [c for c in rec["pool"] if c in nbr]
        k = len(cand); ks.append(k); g = bool(set(cand) & set(rec["gold"]))
        hit += g
        if g: inv.append(1 / k)
    base[arm] = {"gold_among_anchor_candidate_neighbours_share": round(hit / len(ids), 4), "k_median": st.median(ks),
                 "mean_1_over_k_where_gold_among_them": round(st.mean(inv), 4) if inv else None,
                 "uniform_pick_accuracy_over_all_tasks": round(sum(inv) / len(ids), 4)}
res["hinted_neighbour_baseline"] = base
json.dump(res, open(sys.argv[1], "w"), indent=1); print(json.dumps(res, indent=1))
