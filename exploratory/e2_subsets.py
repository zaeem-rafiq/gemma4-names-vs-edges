# EXPLORATORY (not pre-registered). E2: Study B graph effect (true - rewired) on tasks where, in the true graph,
# a gold candidate is a 1-hop neighbour of an anchor (tasks.json b5_anchor_neighbours["true"] & gold), vs the rest.
# Reads only the frozen task files and the Study B run files. Run with python3 -I.
import os
import json, random, statistics as st, sys
from collections import defaultdict
P = os.environ["P"]  # the project folder (redacted in the release; was an absolute path)
R = P + "/studyB-v1.1/runs/"  # the author's folder layout; point it at your copy of these files
TASKS = {"official": P + "/studyb-frozen/official/tasks.json", "lite": P + "/studyb-frozen/lite/tasks.json"}
RUNS = ["studyB_official_E4B", "studyB_official_31B", "studyB_lite_E4B", "studyB_official_12B", "studyB_lite_31B"]
CONF = {("E4B", "official"), ("31B", "official"), ("E4B", "lite")}
tasks = {}
for s, f in TASKS.items():
    for t in json.load(open(f))["tasks"]:
        if t["role"] == "confirmatory" and t["eligible"] and t["anchored"]:
            adj = set(t["b5_anchor_neighbours"]["true"]) & set(t["gold"])
            tasks[t["task_id"]] = {"set": s, "near": bool(adj), "repo": t["repo"], "stratum": t["stratum"]}
pred = {}
cell = defaultdict(dict)  # (model, set, task) -> {(naming, graph, order): correct}
for r in RUNS:
    L = open(R + r + ".jsonl").read().splitlines()[1:]
    for l in L:
        x = json.loads(l)
        if x["item_id"] in tasks and x["graph"] in ("true", "rewired"):
            cell[(x["model"], x["set"], x["item_id"])][(x["naming"], x["graph"], x["perm"])] = int(x["pred_letter"] in x["correct_letters"])
            pred[(x["model"], x["set"], x["item_id"], x["naming"], x["graph"], x["perm"])] = x["pred_letter"]
def diffs(model_set, naming, near, key="near"):
    out = {}
    for (m, s, tid), c in cell.items():
        if (m, s) not in model_set or tasks[tid][key] != near:
            continue
        d = [c[(naming, "true", o)] - c[(naming, "rewired", o)] for o in (1, 2) if (naming, "true", o) in c and (naming, "rewired", o) in c]
        if d:
            out.setdefault(tid, []).append(st.mean(d))
    return [st.mean(v) for v in out.values()]  # per task: mean over orders, then over models
def summ(v, seed=0):
    if not v:
        return {"n_tasks": 0}
    rng = random.Random(seed); n = len(v); m = st.mean(v)
    boots = sorted(st.mean(rng.choices(v, k=n)) for _ in range(10000))
    obs = abs(m); ge = 1
    for _ in range(10000):
        ge += abs(st.mean([x if rng.random() < 0.5 else -x for x in v])) >= obs - 1e-12
    return {"n_tasks": n, "estimate": round(m, 4), "ci95_boot": [round(boots[249], 4), round(boots[9749], 4)], "p_signflip": round(ge / 10001, 4)}
groups = {"confirmatory (E4B+31B official, E4B Lite)": CONF}
for ms in sorted({(m, s) for (m, s, _) in cell}):
    groups[f"{ms[0]} {ms[1]}" + ("" if ms in CONF else " (descriptive)")] = {ms}
res = {"label": "EXPLORATORY, not pre-registered", "n_anchored_confirmatory": len(tasks),
       "n_near": sum(t["near"] for t in tasks.values()), "near_by_set": {s: sum(1 for t in tasks.values() if t["set"] == s and t["near"]) for s in TASKS},
       "anchored_by_set": {s: sum(1 for t in tasks.values() if t["set"] == s) for s in TASKS},
       "definition": "near = a gold function is in b5_anchor_neighbours['true'] (a pool candidate sharing an edge with an anchor in the full true graph); effect = correct(true) - correct(rewired) per order, mean over orders 1-2, then over models, per task",
       "results": {}}
for g, ms in groups.items():
    for naming in ("opaque", "real"):
        for near in (True, False):
            res["results"][f"{g} | {naming} | {'near' if near else 'rest'}"] = summ(diffs(ms, naming, near))
from collections import Counter
res["near_x_stratum"] = {str(k): v for k, v in Counter((t["near"], t["stratum"]) for t in tasks.values()).items()}
res["by_stratum_confirmatory"] = {f"{n} | {sx}": summ(diffs(CONF, n, sx, key="stratum")) for n in ("opaque", "real") for sx in ("S0", "S1", "S2", "S3")}
fl = {}
for (m, s_, tid, n, g, o), p in pred.items():
    if g == "true" and (m, s_, tid, n, "rewired", o) in pred:
        k = f"{m} {s_} {n}"; a = fl.setdefault(k, [0, 0]); a[0] += 1; a[1] += p != pred[(m, s_, tid, n, "rewired", o)]
res["prediction_changed_true_vs_rewired"] = {k: {"pairs": a, "changed": b, "share": round(b / a, 4)} for k, (a, b) in sorted(fl.items())}
w = res["results"]
res["check_B2"] = {"weighted_near_rest_opaque": round((w["confirmatory (E4B+31B official, E4B Lite) | opaque | near"]["estimate"] * res["n_near"] + w["confirmatory (E4B+31B official, E4B Lite) | opaque | rest"]["estimate"] * (len(tasks) - res["n_near"])) / len(tasks), 4), "report_B2": -0.0216}
json.dump(res, open(sys.argv[1], "w"), indent=1)
print(json.dumps(res, indent=1))
