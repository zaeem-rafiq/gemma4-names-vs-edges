# EXPLORATORY (not pre-registered). E4 density-matched graph arms, preparation only (no model).
# For each anchored confirmatory task, two new tool-output contexts built from the frozen context.true/rewired:
#  true_thinned: the true block's directed edges, removed at random by node pair (seeded) until the subgraph's
#                directed edge count equals the rewired block's; the neighbour list of the first anchor is thinned the same way to the
#                rewired list's length.
#  random_dense: the true block's node set with the true block's number of directed subgraph edges, drawn at
#                random among those nodes as mirrored pairs (plus one one-way edge if odd; no self-loops, no duplicates); the neighbour list keeps the true
#                list's length, drawn at random from the block's nodes (subgraph nodes and true neighbours).
# Prompts are rendered with the package (render_fixed); the base opaque/true prompt is checked against its frozen
# SHA-256, and every new prompt must equal it outside the tool-output block. Writes e4_prompts.jsonl (LOCAL ONLY)
# and e4_checks.json (counts and identifiers only).
import os
import json, random, statistics as st, sys
from ngraph import studyb as sb
from ngraph.lite import LiteSource
P = os.environ["P"]  # the project folder (redacted in the release; was an absolute path)
FROZEN = {s: {t["task_id"]: t for t in sb.load_task_file(f"{P}/studyb-frozen/{s}/tasks.json")["tasks"]} for s in ("official", "lite")}
srcs = {"official": sb.OfficialSource(P + "/competition-data"),
        "lite": LiteSource(P + "/lite/swebench_lite_test.jsonl", P + "/lite-repos", P + "/lite/swebench_lite_dev.jsonl")}
def units(edges):
    """The shown directed edges grouped by unordered node pair (a mirrored pair is one unit of 2; a one-way edge
    or a self-loop is a unit of 1)."""
    g = {}
    for a, b in edges:
        g.setdefault(tuple(sorted((a, b))), []).append((a, b))
    return [sorted(v) for _, v in sorted(g.items())]
def thin_to(edges, target, rng):
    """Remove whole units at random until the directed count is <= target, then split one mirrored unit if the
    count is one above target, so the result has exactly `target` directed edges (or all of them if fewer)."""
    us = units(edges); rng.shuffle(us); kept = [e for u in us for e in u]
    while len(kept) > target and us:
        u = us.pop(); kept = [e for x in us for e in x]
        if len(kept) < target:  # overshot by removing a 2-unit: put one direction back
            kept.append(u[0])
    return set(kept)
def dense_like(nodes, n_dir, rng, forbid=frozenset()):
    """n_dir directed edges among `nodes`, drawn as random mirrored pairs (no self-loops, no duplicates), plus one
    random one-way edge when n_dir is odd."""
    allp = [(a, b) for i, a in enumerate(nodes) for b in nodes[i + 1:] if frozenset((a, b)) not in forbid]
    k = min(n_dir // 2, len(allp)); pp = rng.sample(allp, k)
    out = {(a, b) for a, b in pp} | {(b, a) for a, b in pp}
    if n_dir % 2 and len(allp) > k:
        a, b = rng.choice([p for p in allp if p not in pp]); out.add((a, b) if rng.random() < 0.5 else (b, a))
    return out
def build(rec, rng):
    ctx_t, ctx_r = rec["context"]["true"], rec["context"]["rewired"]
    sg_t = ctx_t["subgraph"]; nodes = sg_t["nodes"]
    et = [tuple(e) for e in sg_t["edges"]]; er = [tuple(e) for e in ctx_r["subgraph"]["edges"]]
    thin = {"subgraph": sb.subgraph_call(nodes, thin_to(et, len(er), rng)), "n_anchors": ctx_t["n_anchors"], "n_candidates": ctx_t["n_candidates"]}
    gcand = set(rec["gold"]) & set(rec["pool"]); anc = {x["node"] for x in rec["anchors"]}
    forbid = frozenset(frozenset((g, x)) for g in gcand for x in anc if g != x)
    dense = {"subgraph": sb.subgraph_call(nodes, dense_like(nodes, len(et), rng, forbid)), "n_anchors": ctx_t["n_anchors"], "n_candidates": ctx_t["n_candidates"]}
    if "neighbors" in ctx_t:
        nb_t, a0 = ctx_t["neighbors"], ctx_t["neighbors"]["node"]
        n_r = len(ctx_r["neighbors"]["neighbors"]) if "neighbors" in ctx_r else 0
        # consistent variant (e4c): the neighbour list always contains the anchor's neighbours in the arm's own
        # subgraph block, then is filled at random to the target length (thinned: rewired list length, from the true
        # neighbours; dense: true list length, from the block's nodes and true neighbours)
        def nbrs_in(sg):
            return {b for a, b in sg["edges"] if a == a0 and b != a0} | {a for a, b in sg["edges"] if b == a0 and a != a0}
        must_t = sorted(nbrs_in(thin["subgraph"]))
        rest_t = sorted(set(nb_t["neighbors"]) - set(must_t))
        kept = must_t + rng.sample(rest_t, max(0, min(n_r - len(must_t), len(rest_t))))
        thin["neighbors"] = sb.neighbors_call(a0, {a0: set(kept)})
        must_d = sorted(nbrs_in(dense["subgraph"]))
        # never join a gold candidate and an anchor: no gold candidate in the anchor's list, and when the anchor
        # itself is a gold candidate, no other anchor either
        pool = sorted((set(nodes) | set(nb_t["neighbors"])) - {a0} - set(must_d) - gcand - (anc if a0 in gcand else set()))
        drawn = must_d + rng.sample(pool, max(0, min(len(nb_t["neighbors"]) - len(must_d), len(pool))))
        dense["neighbors"] = sb.neighbors_call(a0, {a0: set(drawn)})
    return thin, dense, len(et), len(er)
out = open(sys.argv[1], "w"); checks = []
for s, src in srcs.items():
    ids = sorted(t for t, r in FROZEN[s].items() if r["role"] == "confirmatory" and r["eligible"] and r["anchored"])
    for tid in ids:
        rec = FROZEN[s][tid]; rng = random.Random(f"e4-{tid}")
        thin, dense, n_t, n_r = build(rec, rng)
        rec2 = dict(rec); rec2["context"] = dict(rec["context"], true_thinned=thin, random_dense=dense)
        keys = [("opaque", g, o) for g in ("true", "rewired", "true_thinned", "random_dense") for o in (1, 2)]
        with src.task_context(tid) as c:
            pr = sb.render_fixed(rec2, c["task"], c["index"], c["renamer"](), rec["render"]["cut_at"], rec["render"]["code_lines"], keys)
        for o in (1, 2):
            base = pr[("opaque", "true", o)]
            if sb.prompt_sha(base) != rec["prompt_sha256"][f"opaque/true/{o}"] or sb.prompt_sha(pr[("opaque", "rewired", o)]) != rec["prompt_sha256"][f"opaque/rewired/{o}"]:
                sys.exit(f"MISMATCH base {tid} {o}")
            head, tail = base.split("\nTool output:\n")[0], base[base.index("\n\n" + sb.QUESTION):]
            for g in ("true_thinned", "random_dense"):
                x = pr[("opaque", g, o)]
                if not (x.startswith(head + "\nTool output:\n") and x.endswith(tail)):
                    sys.exit(f"OUTSIDE-BLOCK DIFF {tid} {g} {o}")
            for g in ("true_thinned", "random_dense"):
                out.write(json.dumps({"task_id": tid, "set": s, "repo": rec["repo"], "graph": g, "order": o,
                                      "correct_letters": rec["correct_letters"][o], "anchored": True, "stratum": rec["stratum"],
                                      "injected": rec["injected"], "text": pr[("opaque", g, o)]}) + "\n")
        gc = set(rec["gold"]) & set(rec["pool"]); anchors = {a["node"] for a in rec["anchors"]}
        def ga(ctx):
            e = [tuple(x) for x in ctx["subgraph"]["edges"]] + ([(ctx["neighbors"]["node"], y) for y in ctx["neighbors"]["neighbors"]] if "neighbors" in ctx else [])
            return int(any((a in gc and b in anchors) or (b in gc and a in anchors) for a, b in e)), len(ctx["subgraph"]["edges"])
        row = {"task_id": tid, "set": s}
        for g, ctx in (("true", rec["context"]["true"]), ("rewired", rec["context"]["rewired"]), ("true_thinned", thin), ("random_dense", dense)):
            row[f"gold_anchor_edge_{g}"], row[f"sub_edges_{g}"] = ga(ctx)
        def consistent(ctx):
            if "neighbors" not in ctx: return 1
            a0 = ctx["neighbors"]["node"]; L = set(ctx["neighbors"]["neighbors"])
            sub = {b for a, b in ctx["subgraph"]["edges"] if a == a0 and b != a0} | {a for a, b in ctx["subgraph"]["edges"] if b == a0 and a != a0}
            return int(sub <= L)
        for g, ctx in (("true", rec["context"]["true"]), ("rewired", rec["context"]["rewired"]), ("true_thinned", thin), ("random_dense", dense)):
            row[f"nb_consistent_{g}"] = consistent(ctx)
        checks.append(row); print(f"{s} {tid} ok", flush=True)
summ = {}
for g in ("true", "rewired", "true_thinned", "random_dense"):
    v = sorted(r[f"sub_edges_{g}"] for r in checks); n = len(v)
    summ[g] = {"sub_edges_median": st.median(v), "iqr": [v[int(.25 * (n - 1))], v[int(.75 * (n - 1))]],
               "gold_anchor_edge_share": round(st.mean(r[f"gold_anchor_edge_{g}"] for r in checks), 4),
               "neighbour_list_consistent_share": round(st.mean(r[f"nb_consistent_{g}"] for r in checks), 4)}
json.dump({"label": "EXPLORATORY, not pre-registered", "n_tasks": len(checks), "summary": summ, "exact_counts": {"thinned_eq_rewired": sum(r["sub_edges_true_thinned"] == r["sub_edges_rewired"] for r in checks), "dense_eq_true": sum(r["sub_edges_random_dense"] == r["sub_edges_true"] for r in checks)}, "tasks": checks}, open(sys.argv[2], "w"), indent=1)
print("ALL DONE", len(checks), json.dumps(summ), flush=True)
