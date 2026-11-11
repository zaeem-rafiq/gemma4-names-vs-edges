# EXPLORATORY (not pre-registered). E1 statistics from e1_tasks.jsonl. Run with python3 -I.
import json, random, statistics as st, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
def summ(v, seed=0):
    v = [x for x in v if x is not None]
    if not v:
        return {"n": 0}
    rng = random.Random(seed); n = len(v); m = st.mean(v)
    boots = sorted(st.mean(rng.choices(v, k=n)) for _ in range(10000))
    ge = 1
    for _ in range(10000):
        ge += abs(st.mean([x if rng.random() < 0.5 else -x for x in v])) >= abs(m) - 1e-12
    return {"n": n, "mean": round(m, 4), "ci95_boot": [round(boots[249], 4), round(boots[9749], 4)], "p_signflip": round(ge / 10001, 4)}
def mean(v):
    v = [x for x in v if x is not None]
    return round(st.mean(v), 4) if v else None
def hit(d, k):
    return int(d is not None and d <= k)
def block(R):
    o = {"n_tasks": len(R), "gold_is_anchor_share": mean([int(r["gold_is_anchor"]) for r in R]),
         "n_lib_median": st.median([r["n_lib"] for r in R]) if R else None}
    for k in (1, 2):
        for lab, key in (("incl_dist0", "dmin_{g}"), ("nonanchor_gold", "dmin_nonanchor_gold_{g}")):
            t = [hit(r[key.format(g="true")], k) for r in R]; w = [hit(r[key.format(g="rewired")], k) for r in R]
            o[f"hit{k}_{lab}"] = {"true": mean(t), "rewired": mean(w), "true_minus_rewired": summ([a - b for a, b in zip(t, w)])}
        nt = [r[f"n{k}_true"] for r in R]; nw = [r[f"n{k}_rewired"] for r in R]
        o[f"n{k}"] = {"true_median": st.median(nt) if nt else None, "rewired_median": st.median(nw) if nw else None,
                      "chance_share_true_mean": mean([a / r["n_lib"] for a, r in zip(nt, R)]),
                      "chance_share_rewired_mean": mean([a / r["n_lib"] for a, r in zip(nw, R)])}
    for var in ("", "noanchor_"):
        bm = "rank_bm25_noanchor" if var else "rank_bm25"
        for lab, f in (("acc1", lambda x: int(x == 1)), ("hit10", lambda x: int(x is not None and x <= 10))):
            t = [f(r[f"rank_{var}true"]) for r in R]; w = [f(r[f"rank_{var}rewired"]) for r in R]; b = [f(r[bm]) for r in R]
            o[f"retriever_{var or 'all_'}{lab}"] = {"bm25_only": mean(b), "true": mean(t), "rewired": mean(w),
                                                   "true_minus_rewired": summ([x - y for x, y in zip(t, w)]),
                                                   "true_minus_bm25": summ([x - y for x, y in zip(t, b)])}
    return o
res = {"label": "EXPLORATORY, not pre-registered", "source": sys.argv[1], "overall": block(rows)}
for s in ("official", "lite"):
    res["set_" + s] = block([r for r in rows if r["set"] == s])
res["injected_subset"] = block([r for r in rows if r["injected"]])
for sx in ("S0", "S1", "S2", "S3"):
    res["stratum_" + sx] = block([r for r in rows if r["stratum"] == sx])
json.dump(res, open(sys.argv[2], "w"), indent=1); print(json.dumps(res["overall"], indent=1))
