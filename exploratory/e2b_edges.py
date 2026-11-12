# EXPLORATORY (not pre-registered). E2b: what the graph block shown in the scored Study B prompts contains, per arm
# (true vs rewired), for the 174 anchored confirmatory tasks. Source: the frozen task files' context.<arm>, which hold
# exactly the tool outputs rendered into the prompts (both orders share them; the block is built from candidate
# order 1 and is identical across naming conditions, renaming only relabels names). Run with python3 -I.
import os
import json, random, statistics as st, sys
P = os.environ["P"]  # the project folder (redacted in the release; was an absolute path)
def q(v):
    v = sorted(v); n = len(v)
    return {"median": st.median(v), "iqr": [v[int(0.25 * (n - 1))], v[int(0.75 * (n - 1))]]} if v else None
def boot(d, seed=0):
    rng = random.Random(seed); n = len(d); m = st.mean(d)
    b = sorted(st.mean(rng.choices(d, k=n)) for _ in range(10000))
    return {"mean_diff": round(m, 4), "ci95": [round(b[249], 4), round(b[9749], 4)]}
rows = []
for s, lab in (("official", "competition"), ("lite", "Lite")):
    for t in json.load(open(f"{P}/studyb-frozen/{s}/tasks.json"))["tasks"]:
        if not (t["role"] == "confirmatory" and t["eligible"] and t["anchored"]):
            continue
        anchors = {a["node"] for a in t["anchors"]}; gc = set(t["gold"]) & set(t["pool"])
        r = {"task_id": t["task_id"], "set": lab}
        for arm in ("true", "rewired"):
            ctx = t["context"][arm]; sg = ctx["subgraph"]
            edges = [tuple(e) for e in sg["edges"]]
            nb = ctx.get("neighbors")
            if nb:
                edges += [(nb["node"], x) for x in nb["neighbors"]]
            r[f"ga_{arm}"] = int(any((a in gc and b in anchors) or (b in gc and a in anchors) for a, b in edges))
            r[f"g_{arm}"] = int(any(a in gc or b in gc for a, b in edges))
            r[f"edges_{arm}"] = len(edges)
            block = {"subgraph": {"nodes": sg["nodes"], "edges": sg["edges"]}, "neighbors": nb}
            r[f"chars_{arm}"] = len(json.dumps(block))
            r[f"trunc_{arm}"] = int(bool(sg.get("is_truncated")) or bool(nb and nb.get("is_truncated")))
        rows.append(r)
res = {"label": "EXPLORATORY, not pre-registered", "n_tasks": len(rows),
       "definition": "graph block = subgraph edges among anchors and candidates plus get_code_neighbors(first anchor) edges, as stored in the frozen task files' context (real names; chars = JSON length with real names, a proxy for the renamed block)",
       "by_set": {}}
for lab in ("competition", "Lite", "all"):
    R = [r for r in rows if lab == "all" or r["set"] == lab]
    o = {"n_tasks": len(R)}
    for k, name in (("ga", "a_gold_anchor_edge_share"), ("g", "b_any_gold_edge_share")):
        o[name] = {"true": round(st.mean(r[f"{k}_true"] for r in R), 4), "rewired": round(st.mean(r[f"{k}_rewired"] for r in R), 4),
                   "true_minus_rewired": boot([r[f"{k}_true"] - r[f"{k}_rewired"] for r in R])}
    o["c_edges"] = {"true": q([r["edges_true"] for r in R]), "rewired": q([r["edges_rewired"] for r in R]),
                    "true_minus_rewired": boot([r["edges_true"] - r["edges_rewired"] for r in R])}
    o["c_block_chars"] = {"true": q([r["chars_true"] for r in R]), "rewired": q([r["chars_rewired"] for r in R])}
    o["truncated_share"] = {"true": round(st.mean(r["trunc_true"] for r in R), 4), "rewired": round(st.mean(r["trunc_rewired"] for r in R), 4)}
    res["by_set"][lab] = o
json.dump(res, open(sys.argv[1], "w"), indent=1); print(json.dumps(res["by_set"], indent=1))
