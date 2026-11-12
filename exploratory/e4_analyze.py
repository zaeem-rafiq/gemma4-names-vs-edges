# EXPLORATORY (not pre-registered). E4 analysis: density-matched arms against the registered opaque true and rewired
# cells on the same tasks. Per task: mean over orders; then the mean over tasks. Gold probability = softmax over the
# 10 letter logits, summed over the correct letters. Task bootstrap (10,000 draws, seed 0). Run with python3 -I.
import os
import json, math, random, statistics as st, sys
P = os.environ["P"]  # the project folder (redacted in the release; was an absolute path)
X = P + "/exploratory-v1.1/"  # the author's folder layout; point it at your copy of these files
L = "ABCDEFGHIJ"
def gold_p(r):
    z = [r[f"logit_{c}"] for c in L]; mx = max(z); e = [math.exp(v - mx) for v in z]; s = sum(e)
    return sum(e[L.index(c)] for c in r["correct_letters"]) / s
def load(paths, naming, graphs):
    c = {}
    for p in paths:
        with open(p) as f:
            next(f)
            for l in f:
                r = json.loads(l)
                if r.get("naming") == naming and r.get("graph") in graphs and r.get("anchored"):
                    c[(r["model"], r["item_id"], r["graph"], r["perm"])] = (int(r["pred_letter"] in r["correct_letters"]), gold_p(r))
    return c
def boot(d, seed=0):
    rng = random.Random(seed); n = len(d)
    b = sorted(st.mean(rng.choices(d, k=n)) for _ in range(10000))
    return {"n": n, "mean": round(st.mean(d), 4), "ci95": [round(b[249], 4), round(b[9749], 4)]}
R = P + "/studyB-v1.1/runs/"
reg = load([R + f for f in ("studyB_official_E4B.jsonl", "studyB_lite_E4B.jsonl", "studyB_official_31B.jsonl", "studyB_lite_31B.jsonl")], "opaque", {"true", "rewired"})
new = {}
for m in ("E4B", "31B"):
    try:
        new.update(load([X + f"e4c_{m}.jsonl"], "opaque", {"true_thinned", "random_dense"}))
    except FileNotFoundError:
        pass
allc = {**reg, **new}
res = {"label": "EXPLORATORY, not pre-registered", "models": {}}
for m in ("E4B", "31B"):
    tasks = sorted({k[1] for k in new if k[0] == m})
    if not tasks: continue
    def per(g, idx):
        out = {}
        for t in tasks:
            v = [allc.get((m, t, g, o)) for o in (1, 2)]
            if all(v): out[t] = st.mean(x[idx] for x in v)
        return out
    o = {"n_tasks": len(tasks), "acc": {}, "gold_prob": {}}
    A = {g: per(g, 0) for g in ("true", "rewired", "true_thinned", "random_dense")}
    G = {g: per(g, 1) for g in A}
    for g in A:
        o["acc"][g] = round(st.mean(A[g].values()), 4); o["gold_prob"][g] = round(st.mean(G[g].values()), 4)
    for a, b in (("true", "random_dense"), ("true_thinned", "rewired"), ("true", "rewired")):
        ks = [t for t in tasks if t in A[a] and t in A[b]]
        o[f"acc_{a}_minus_{b}"] = boot([A[a][t] - A[b][t] for t in ks])
        o[f"goldprob_{a}_minus_{b}"] = boot([G[a][t] - G[b][t] for t in ks])
    o["note"] = "31B Lite registered cells are descriptive in Study B" if m == "31B" else ""
    res["models"][m] = o
json.dump(res, open(sys.argv[1], "w"), indent=1); print(json.dumps(res, indent=1))
