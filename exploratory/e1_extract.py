# EXPLORATORY (not pre-registered). E1 extraction: per anchored confirmatory task, regenerate the Study B graph,
# its rewired copy (seed 1) and the task record through the package path (task_context + build_task), check it
# against the frozen record, then write hop distances, n_k and retriever ranks. Name collection is stubbed out
# (E1 uses no names); the gate on every task shows the stub changes nothing. Run with PYTHONPATH=<studyB-v1.1>/src.
import os
import json, sys, time
from collections import deque
from ngraph import studyb as sb, localize as lz
from ngraph.lite import LiteSource
P = os.environ["P"]  # the project folder (redacted in the release; was an absolute path)
out = open(sys.argv[1], "a")
done = set()
try:
    done = {json.loads(l)["task_id"] for l in open(sys.argv[1])}
except Exception:
    pass
FROZEN = {s: {t["task_id"]: t for t in json.load(open(f"{P}/studyb-frozen/{s}/tasks.json"))["tasks"]} for s in ("official", "lite")}
CHECK = ("anchors", "pool", "gold", "b5_anchor_neighbours", "injected", "gold_ranks", "stratum")
def bfs(starts, nb):
    d = {s: 0 for s in starts}; q = deque(starts)
    while q:
        u = q.popleft()
        for v in nb.get(u, ()):
            if v not in d:
                d[v] = d[u] + 1; q.append(v)
    return d
def nbrs(edges):
    nb = {}
    for s, t, _ in edges:
        if s != t:
            nb.setdefault(s, set()).add(t); nb.setdefault(t, set()).add(s)
    return nb
def rank(order, gold):
    for i, n in enumerate(order, 1):
        if n in gold:
            return i
    return None
srcs = {"official": sb.OfficialSource(P + "/competition-data"),
        "lite": LiteSource(P + "/lite/swebench_lite_test.jsonl", P + "/lite-repos", P + "/lite/swebench_lite_dev.jsonl")}
for s, src in srcs.items():
    src.repo_names = lambda repo: None  # E1 uses no names
    ids = sorted(t for t, r in FROZEN[s].items() if r["role"] == "confirmatory" and r["eligible"] and r["anchored"])
    for tid in ids:
        if tid in done:
            continue
        t0 = time.time(); fz = FROZEN[s][tid]
        with src.task_context(tid) as c:
            rec = sb.build_task(c["task"], c["graph"], c["rewired"], c["index"], c["lib_ids"], set_name=s)
            J = lambda v: json.loads(json.dumps(v))
            mism = [k for k in CHECK if J(rec.get(k)) != J(fz.get(k))]
            for g in ("true", "rewired"):
                if J(rec["context"][g]) != J(fz["context"][g]):
                    mism.append("context." + g)
            if mism:
                print(json.dumps({"task_id": tid, "MISMATCH": mism}), flush=True); sys.exit(3)
            issue = sb.normalise_issue(c["task"]["problem_statement"])
            lib = sorted(set(c["lib_ids"]))
            docs = {nid: nid + "\n" + c["index"].source(nid) for nid in lib}
            sc = lz.BM25(docs).scores(issue)
            bad = [n for n, v in fz["bm25_pool_scores"].items() if round(sc[n], 6) != v]
            if bad:
                print(json.dumps({"task_id": tid, "MISMATCH": ["bm25"], "n": len(bad)}), flush=True); sys.exit(4)
            anchors = [a["node"] for a in fz["anchors"]]; gold = set(fz["gold"]); libset = set(lib)
            row = {"task_id": tid, "set": s, "repo": fz["repo"], "stratum": fz["stratum"], "injected": fz["injected"],
                   "n_lib": len(lib), "n_graph_nodes": len(c["graph"]["nodes"]), "n_anchors": len(anchors),
                   "gold_is_anchor": bool(gold & set(anchors)), "n_gold": len(gold)}
            bm = sorted(lib, key=lambda n: (-sc[n], n))
            row["rank_bm25"] = rank(bm, gold)
            row["rank_bm25_noanchor"] = rank([n for n in bm if n not in anchors], gold)
            for g, edges in (("true", c["graph"]["edges"]), ("rewired", c["rewired"])):
                d = bfs(anchors, nbrs(edges)); inf = 10 ** 9
                dg = [d.get(x, inf) for x in gold]
                ng = [d.get(x, inf) for x in gold if x not in anchors]
                row[f"dmin_{g}"] = min(dg) if min(dg) < inf else None
                row[f"dmin_nonanchor_gold_{g}"] = (min(ng) if ng and min(ng) < inf else None)
                for k in (1, 2):
                    row[f"n{k}_{g}"] = sum(1 for n in lib if n not in anchors and 1 <= d.get(n, inf) <= k)
                order = sorted(lib, key=lambda n: (d.get(n, inf), -sc[n], n))
                row[f"rank_{g}"] = rank(order, gold)
                row[f"rank_noanchor_{g}"] = rank([n for n in order if n not in anchors], gold)
        row["secs"] = round(time.time() - t0, 1)
        out.write(json.dumps(row) + "\n"); out.flush()
        print(f"{s} {tid} ok {row['secs']}s", flush=True)
print("ALL DONE", flush=True)
