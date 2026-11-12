# EXPLORATORY (not pre-registered). E3 positive control, preparation only (no model is loaded).
# Tasks: anchored confirmatory tasks where a gold candidate is a 1-hop neighbour of the FIRST anchor in the true
# graph. Prompts: the frozen Study B opaque prompts (true, rewired, none; orders 1 and 2), rebuilt and checked
# against their frozen SHA-256, plus one hint line inserted right before the answer request.
# Writes e3_tasks.json (ids and identifiers only) and e3_prompts.jsonl (full prompt text: LOCAL ONLY, never released).
import os
import json, sys
from ngraph import studyb as sb
from ngraph.lite import LiteSource
P = os.environ["P"]  # the project folder (redacted in the release; was an absolute path)
# The scored E3 prompts use the hint below. They were made from this script's first output (hint "... in the call
# graph above.", kept as hint_v1_superseded in e3_tasks.json) by replacing only that hint text, and a "hint" field was
# added to each prompt record; running this script reproduces the same prompt texts.
HINT = "Hint: the function to edit is a direct neighbour of {a} in the repository's call graph."
FROZEN = {s: {t["task_id"]: t for t in sb.load_task_file(f"{P}/studyb-frozen/{s}/tasks.json")["tasks"]} for s in ("official", "lite")}
srcs = {"official": sb.OfficialSource(P + "/competition-data"),
        "lite": LiteSource(P + "/lite/swebench_lite_test.jsonl", P + "/lite-repos", P + "/lite/swebench_lite_dev.jsonl")}
tasks, out = [], open(sys.argv[1], "w")
for s, src in srcs.items():
    ids = sorted(t for t, r in FROZEN[s].items() if r["role"] == "confirmatory" and r["eligible"] and r["anchored"])
    for tid in ids:
        rec = FROZEN[s][tid]; first = rec["anchors"][0]["node"]
        gold_c = [g for g in rec["gold"] if g in rec["pool"]]
        with src.task_context(tid) as c:
            nb = set()
            for a, b, _ in c["graph"]["edges"]:
                if a != b and first in (a, b):
                    nb.add(b if a == first else a)
            hit = sorted(set(gold_c) & nb)
            if not hit:
                continue
            ren = c["renamer"]()
            keys = [("opaque", g, o) for g in ("true", "rewired", "none") for o in (1, 2)]
            prompts = sb.render_fixed(rec, c["task"], c["index"], ren, rec["render"]["cut_at"], rec["render"]["code_lines"], keys)
            first_ren = ren.rename_code(first).text
        for (n, g, o), text in prompts.items():
            if sb.prompt_sha(text) != rec["prompt_sha256"][f"{n}/{g}/{o}"]:
                sys.exit(f"MISMATCH {tid} {n}/{g}/{o}")
            assert text.count(sb.QUESTION) == 1
            hinted = text.replace(sb.QUESTION, HINT.format(a=first_ren) + "\n" + sb.QUESTION)
            out.write(json.dumps({"task_id": tid, "set": s, "repo": rec["repo"], "graph": g, "order": o,
                                  "correct_letters": rec["correct_letters"][o],
                                  "anchored": True, "stratum": rec["stratum"], "injected": rec["injected"],
                                  "text": hinted, "base_sha256": rec["prompt_sha256"][f"{n}/{g}/{o}"]}) + "\n")
        tasks.append({"task_id": tid, "set": s, "repo": rec["repo"], "first_anchor": first, "first_anchor_renamed": first_ren,
                      "gold_neighbours_of_first_anchor": hit, "stratum": rec["stratum"]})
        print(f"{s} {tid} selected", flush=True)
json.dump({"label": "EXPLORATORY, not pre-registered", "hint": HINT, "n_tasks": len(tasks), "tasks": tasks},
          open(sys.argv[2], "w"), indent=1)
print("ALL DONE", len(tasks), flush=True)
