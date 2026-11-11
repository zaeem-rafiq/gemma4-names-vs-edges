# Writes every rendered prompt of the official set to a gzip JSON in the staging folder (never reported; local comparison only).
# Usage: PYTHONPATH=<src of the renamer version> PKG/.venv/bin/python studyb5_dump_prompts.py <data> <vocab> <out.json.gz>
import gzip, json, sys
from ngraph import studyb as sb, rename as rn
data, vocab, out = sys.argv[1:4]
store = {}; orig = sb.render_task
def wrap(rec, t, index, renamer, count, *a, **k):
    r = orig(rec, t, index, renamer, count, *a, **k)
    store[rec["task_id"]] = {f"{n}/{g}/{o}": x for (n, g, o), x in r["prompts"].items()}
    return r
sb.render_task = wrap
res = sb.build_records(sb.OfficialSource(data), "official", sb.vocab_counter(vocab), None, log=lambda x: None)
sha = {r["task_id"]: r["prompt_sha256"] for r in res["records"] if r["eligible"]}
with gzip.open(out, "wt") as f:
    json.dump({"rename_version": rn.RENAME_VERSION, "prompts": store, "sha": sha, "maps": res["rename_maps"]}, f)
print(rn.RENAME_VERSION, len(store))
