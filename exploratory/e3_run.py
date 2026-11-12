# EXPLORATORY (not pre-registered). Score prepared E3/E4 prompts with the Study B scorer and settings.
# Usage (cwd = the unpacked prereg-v1.1 package, PYTHONPATH=src):
#   e3_run.py <prompts.jsonl> <out.jsonl> <model.gguf> <TAG> [--prefix-from SMOKE] [--study E3]
import argparse, json, os, platform, sys, time
from ngraph import runner as rr, studyb as sb
ap = argparse.ArgumentParser()
ap.add_argument("prompts"); ap.add_argument("out"); ap.add_argument("model"); ap.add_argument("tag")
ap.add_argument("--prefix-from"); ap.add_argument("--study", default="E3")
ap.add_argument("--items-dir", default="data/items"); ap.add_argument("--manifest", default="data/repos_manifest.json")
a = ap.parse_args()
tag = a.tag.upper(); tb = rr.thought_mode_for(tag, "auto")
model_gguf = rr.gguf_info(a.model)
if a.prefix_from:
    rr.read_smoke(a.prefix_from, tag)
    groups, man_roles = rr._load_manifest(a.manifest)
    pilot = None if man_roles is None else [k for k, v in man_roles.items() if v == "pilot"]
    prefix, prefix_source = rr.prefix_from_smoke(a.prefix_from, tag, model_gguf.get("sha256"), tb, rr.package_state(a.items_dir), pilot)
else:
    prefix = rr.answer_prefix_for(tag, None, required=True); prefix_source = {"rule": "ANSWER_PREFIX"}
rows = [json.loads(l) for l in open(a.prompts)]
naming = "opaque_hint" if a.study == "E3" else "opaque"
jobs = [{**sb.job_key(r["task_id"], naming, r["graph"], r["order"]), "set": r["set"], "repo": r["repo"], "naming": naming,
         "graph": r["graph"], "order": r["order"], "anchored": r["anchored"], "stratum": r["stratum"], "injected": r["injected"],
         "role": "exploratory", "correct_letters": r["correct_letters"], "text": r["text"]}
        for r in sorted(rows, key=lambda r: (r["task_id"], r["graph"], r["order"]))]
scorer = rr.LetterScorer(a.model, n_ctx=sb.N_CTX, n_batch=512, n_gpu_layers=-1, flash_attn=False, thought_block=tb, answer_prefix=prefix)
header = {"study": a.study + " (EXPLORATORY, not pre-registered)", "model_tag": tag, "model_file": os.path.basename(a.model),
          "settings": scorer.settings, "answer_prefix_source": prefix_source, "model_gguf": model_gguf, "model_n_params": scorer.n_params,
          "package": rr.package_state(None), "prompts_file": os.path.basename(a.prompts),
          "prompts_sha256": __import__("hashlib").sha256(open(a.prompts, "rb").read()).hexdigest(),
          "perms": [1, 2], "versions": sorted({j["version"] for j in jobs}), "letter_ids": scorer.letter_ids(sb.LETTERS10),
          "repos": sorted({j["repo"] for j in jobs}), "n_tasks": len({j["item_id"] for j in jobs}), "n_jobs": len(jobs),
          "platform": platform.platform(), "python": sys.version.split()[0], "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
print(json.dumps(rr.run_jobs(scorer, jobs, a.out, tag, header, letters=sb.LETTERS10)))
