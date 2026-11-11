# Read-only diagnosis of "could not find a valid opaque renaming". Uses our package only (ast parsing, no execution).
# Usage: python -I diag_renamer.py P owner/name [more repos]
import collections, json, os, sys
P = sys.argv[1]; sys.path.insert(0, os.path.join(P, "gemma4-paper-code", "src"))
from ngraph import lite, rename as rn
src = lite.__dict__[[k for k, v in lite.__dict__.items() if isinstance(v, type) and hasattr(v, "repo_names")][0]](P + "/lite/swebench_lite_test.jsonl", P + "/lite-repos", P + "/lite/swebench_lite_dev.jsonl")
orig = rn.OpaqueNamer._valid
last = {}
def valid(self, comp, new, owner):
    low = new.lower(); why = []
    if new == comp: why.append("same")
    if low in rn.RESERVED: why.append("reserved")
    if new in self.taken_names: why.append("taken")
    fb = [f for f in self.forbidden if f in low]
    if fb: why.append("forbidden:" + ",".join(sorted(fb)))
    import re
    if any(self.reject(p.lower()) for p in re.split(r"[_-]", new) if len(p) > 1 and p.isalpha()): why.append("reject")
    if owner.get(new, comp) != comp: why.append("owner_clash")
    r = orig(self, comp, new, owner)
    if not r: last.setdefault(comp, collections.Counter())[";".join(why) or "unknown"] += 1
    return r
rn.OpaqueNamer._valid = valid
out = {}
for repo in sys.argv[2:]:
    last.clear()
    names = src.repo_names(repo)
    rec = {"identity": sorted(names.identity), "packages": sorted(names.packages), "protected_n": len(names.protected), "renamable_n": len(names.renamable())}
    try:
        rn.OpaqueRenamer(names, seed=1); rec["result"] = "ok"
    except RuntimeError as e:
        rec["result"] = "RuntimeError: " + str(e)
        rec["rejected_counts_per_name"] = {k: dict(v.most_common(6)) for k, v in sorted(last.items(), key=lambda kv: -sum(kv[1].values()))[:15]}
    out[repo] = rec; print(repo, rec["result"], flush=True)
json.dump(out, open(P + "/run_log/studyb_diag/renamer.json", "w"), indent=1)
print(json.dumps(out, indent=1)[:6000])
