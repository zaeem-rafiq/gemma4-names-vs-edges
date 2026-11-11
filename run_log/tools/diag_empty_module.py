# Which files give a module name with an empty first component? Our package only; nothing is executed.
import json, os, sys, tempfile
P = sys.argv[1]; sys.path.insert(0, os.path.join(P, "gemma4-paper-code", "src"))
from ngraph import lite, rename as rn
src = lite.LiteSource(P + "/lite/swebench_lite_test.jsonl", P + "/lite-repos", P + "/lite/swebench_lite_dev.jsonl")
out = {}
for repo in sys.argv[2:]:
    bc = sorted({t["base_commit"] for t in src.tasks.values() if t["repo"] == repo})
    hits = {}
    for sha in bc:
        with tempfile.TemporaryDirectory() as tmp:
            root = lite.snapshot(lite.clone_dir(src.repos_dir, repo), sha, tmp)
            files = rn.repo_python_files(root); strip = not rn.src_is_package(root, files)
            for rel in files:
                mod, _ = rn.module_name_for(rel, strip)
                if mod and "" in mod.split("."):
                    hits.setdefault(rel, {"module": mod, "commits": 0})["commits"] += 1
    out[repo] = {"commits": len(bc), "files": hits}; print(repo, len(bc), hits, flush=True)
json.dump(out, open(P + "/run_log/studyb_diag/empty_module.json", "w"), indent=1)
