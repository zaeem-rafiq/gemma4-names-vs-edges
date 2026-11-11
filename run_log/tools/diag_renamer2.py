# Read-only: why the empty name passes in some repos, and what the "taken" rejections compose to. Our package only.
import json, os, sys
P = sys.argv[1]; sys.path.insert(0, os.path.join(P, "gemma4-paper-code", "src"))
from ngraph import lite, rename as rn
src = lite.LiteSource(P + "/lite/swebench_lite_test.jsonl", P + "/lite-repos", P + "/lite/swebench_lite_dev.jsonl")
print("shape('') =", rn.shape(""))
for c in ("a11", "a1_", "a2_"): print("shape", c, rn.shape(c))
orig = rn.OpaqueNamer._valid; seen = {}
def valid(self, comp, new, owner):
    r = orig(self, comp, new, owner)
    if not r and (comp == "" or comp in ("a11", "a1_", "a2_")):
        seen.setdefault(comp, []).append([new, new in self.taken_names, [self.sub_map.get(t) for t in self._subs(comp)]])
    return r
rn.OpaqueNamer._valid = valid
for repo in sys.argv[2:]:
    seen.clear(); n = src.repo_names(repo); prot_low = {p.lower() for p in n.protected}
    print(repo, "'' in protected:", "" in n.protected, "'' in prot_low:", "" in prot_low, "'' in renamable:", "" in n.renamable())
    try: rn.OpaqueRenamer(n, seed=1); print(" ok")
    except RuntimeError as e: print(" ", e)
    for k, v in seen.items(): print(" ", repr(k), len(v), "tries; last 4:", v[-4:], "distinct new:", len({x[0] for x in v}))
