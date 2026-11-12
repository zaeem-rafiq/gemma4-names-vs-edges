# EXPLORATORY (not pre-registered). E5 format bridge, preparation only (no model). For the Study A items each model
# was scored on, re-render G1 and G3 with the graph shown as Study B's JSON tool output instead of "F -> G, H"
# lines. Everything else (question, options, option order, footer) is byte-identical to the registered prompt.
# G0 shows no graph, so it is not re-rendered (its registered cells are the baseline). Our own Study A items only.
# Usage (PYTHONPATH=<prereg-v1.1>/src): e5_prepare.py <items_dir> <studyA_runs_dir> <out.jsonl> <summary.json>
import glob, json, os, re, sys
from ngraph import studyb as sb
from ngraph.items import HEADER
items_dir, runs_dir, out_p, summ_p = sys.argv[1:5]
NEW_HEAD = "Below is the output of a code-graph tool for part of the static call graph of the Python repository {repo}."
items = {}
for f in glob.glob(os.path.join(items_dir, "*.json")):
    for it in json.load(open(f))["items"]:
        items[it["item_id"]] = it
used = {}
for f in sorted(glob.glob(os.path.join(runs_dir, "studyA_*.jsonl"))):
    m = os.path.basename(f)[7:-6]
    with open(f) as fh:
        next(fh)
        used[m] = sorted({json.loads(l)["item_id"] for l in fh if '"item_id"' in l})
LINE = re.compile(r"^(\S+) -> (.+)$")
def convert(text, repo):
    head = HEADER.format(repo=repo)
    assert text.startswith(head + "\n\n"), "header"
    body = text[len(head) + 2:]
    block, rest = body.split("\n\nQuestion: ", 1)
    nodes, edges = [], set()
    for ln in block.split("\n"):
        mm = LINE.match(ln); assert mm, ln
        s, ts = mm.group(1), mm.group(2); nodes.append(s)
        if ts != "(none)":
            for t in ts.split(", "): edges.add((s, t))
    # same shape as studyb.subgraph_call, without its 5,000-character list cap (Study A shows every edge)
    sg = {"nodes": nodes, "edges": sorted(edges), "is_truncated": False}
    tool = sb.render_tool_output({"subgraph": sg, "n_anchors": 0, "n_candidates": len(nodes)}, lambda x: x)
    tool = tool.replace(f"get_code_subgraph(<the {len(nodes)} candidates>)", f"get_code_subgraph(<the {len(nodes)} functions shown>)")
    return f"{NEW_HEAD.format(repo=repo)}\n\n{tool}\n\nQuestion: {rest}", len(nodes), len(edges)
out = open(out_p, "w"); counts = {}
for m, ids in used.items():
    n = 0
    for iid in ids:
        it = items[iid]
        for perm, vkey in ((1, "versions"), (2, "versions_perm2")):
            for g in ("G1", "G3"):
                v = it[vkey][g]
                t, nn, ne = convert(v["text"], it["repo"])
                out.write(json.dumps({"model": m, "item_id": iid, "repo": it["repo"], "version": g + "J", "perm": perm,
                                      "correct_letter": v["correct"], "qtype": it["qtype"], "n_nodes": nn, "n_edges": ne,
                                      "text": t, "registered_sha256": sb.prompt_sha(v["text"])}) + "\n"); n += 1
    counts[m] = {"items": len(ids), "prompts": n}
json.dump({"label": "EXPLORATORY, not pre-registered", "new_header": NEW_HEAD, "counts": counts}, open(summ_p, "w"), indent=1)
print(json.dumps(counts))
