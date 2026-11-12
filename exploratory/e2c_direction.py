# EXPLORATORY fact check (no model): are the shown subgraph edges mirrored? Frozen task files' context.<arm>.subgraph
# edges for all eligible confirmatory tasks. get_code_neighbors output is a plain neighbour list (studyb.neighbors_call
# builds it from undirected adjacency), so it carries no direction and is reported separately. Run with python3 -I.
import os
import json, sys
P = os.environ["P"]  # the project folder (redacted in the release; was an absolute path)
res = {"label": "EXPLORATORY fact check", "neighbors_output": "undirected neighbour list (no direction)", "by_set": {}}
for s, lab in (("official", "competition"), ("lite", "Lite")):
    T = [t for t in json.load(open(f"{P}/studyb-frozen/{s}/tasks.json"))["tasks"] if t["role"] == "confirmatory" and t["eligible"]]
    o = {"n_tasks": len(T)}
    for arm in ("true", "rewired"):
        ne = nrev = nloop = tasks_loop = tasks_oneway = tasks_edges = 0
        for t in T:
            E = [tuple(e) for e in t["context"][arm]["subgraph"]["edges"]]; S = set(E)
            loops = [e for e in E if e[0] == e[1]]; nonloop = [e for e in E if e[0] != e[1]]
            ne += len(nonloop); nrev += sum((b, a) in S for a, b in nonloop)
            nloop += len(loops); tasks_loop += bool(loops); tasks_edges += bool(E)
            tasks_oneway += any((b, a) not in S for a, b in nonloop)
        o[arm] = {"non_loop_directed_edges": ne, "reverse_also_shown_share": round(nrev / ne, 4) if ne else None,
                  "tasks_with_any_edge": tasks_edges, "tasks_with_one_way_edge": tasks_oneway,
                  "tasks_with_one_way_edge_share": round(tasks_oneway / len(T), 4),
                  "self_loops": nloop, "tasks_with_self_loop": tasks_loop}
    res["by_set"][lab] = o
json.dump(res, open(sys.argv[1], "w"), indent=1); print(json.dumps(res, indent=1))
