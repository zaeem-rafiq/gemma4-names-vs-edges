# EXPLORATORY (not pre-registered). E5: score the JSON-format Study A prompts exactly like Study A (4 letters).
# Usage (cwd = the unpacked prereg-v1.1 package, PYTHONPATH=src):
#   e5_run.py <e5_prompts.jsonl> <out.jsonl> <model.gguf> <TAG> --versions G1J,G3J [--perms 1] [--prefix-from SMOKE]
import argparse, hashlib, json, os, platform, sys, time
from ngraph import runner as rr
ap = argparse.ArgumentParser()
ap.add_argument("prompts"); ap.add_argument("out"); ap.add_argument("model"); ap.add_argument("tag")
ap.add_argument("--versions", default="G1J,G3J"); ap.add_argument("--perms", default="1,2"); ap.add_argument("--prefix-from")
ap.add_argument("--items-dir", default="data/items"); ap.add_argument("--manifest", default="data/repos_manifest.json")
a = ap.parse_args()
tag = a.tag.upper(); tb = rr.thought_mode_for(tag, "auto"); model_gguf = rr.gguf_info(a.model)
if a.prefix_from:
    rr.read_smoke(a.prefix_from, tag)
    groups, man_roles = rr._load_manifest(a.manifest)
    pilot = None if man_roles is None else [k for k, v in man_roles.items() if v == "pilot"]
    prefix, prefix_source = rr.prefix_from_smoke(a.prefix_from, tag, model_gguf.get("sha256"), tb, rr.package_state(a.items_dir), pilot)
else:
    prefix = rr.answer_prefix_for(tag, None, required=True); prefix_source = {"rule": "ANSWER_PREFIX"}
vers, perms = set(a.versions.split(",")), {int(p) for p in a.perms.split(",")}
rows = [json.loads(l) for l in open(a.prompts)]
jobs = [{"item_id": r["item_id"], "version": r["version"], "perm": r["perm"], "repo": r["repo"], "qtype": r["qtype"],
         "correct_letter": r["correct_letter"], "text": r["text"]}
        for r in rows if r["model"] == tag and r["version"] in vers and r["perm"] in perms]
jobs.sort(key=lambda j: (j["item_id"], j["version"], j["perm"]))
scorer = rr.LetterScorer(a.model, n_ctx=8192, n_batch=512, n_gpu_layers=-1, flash_attn=False, thought_block=tb, answer_prefix=prefix)
header = {"study": "E5 (EXPLORATORY, not pre-registered)", "model_tag": tag, "model_file": os.path.basename(a.model),
          "settings": scorer.settings, "answer_prefix_source": prefix_source, "model_gguf": model_gguf, "model_n_params": scorer.n_params,
          "package": rr.package_state(None), "prompts_file": os.path.basename(a.prompts),
          "prompts_sha256": hashlib.sha256(open(a.prompts, "rb").read()).hexdigest(), "perms": sorted(perms),
          "versions": sorted(vers), "letter_ids": scorer.letter_ids(rr.LETTERS4), "repos": sorted({j["repo"] for j in jobs}),
          "n_jobs": len(jobs), "platform": platform.platform(), "python": sys.version.split()[0],
          "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
print(json.dumps(rr.run_jobs(scorer, jobs, a.out, tag, header, letters=rr.LETTERS4)))
