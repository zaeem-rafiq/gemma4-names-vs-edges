# Compares official-set prompts of renamer 0.1.1 and 0.1.2. Run with -I. Output: counts and identifiers only.
import collections, difflib, gzip, json, re, sys
old_f, new_f, oldt, newt, out = sys.argv[1:6]
O = json.load(gzip.open(old_f, "rt")); N = json.load(gzip.open(new_f, "rt"))
ot = {t["task_id"]: t for t in json.load(open(oldt))["tasks"]}; nt = {t["task_id"]: t for t in json.load(open(newt))["tasks"]}
W = re.compile(r"[A-Za-z0-9_]+|[^A-Za-z0-9_]+")
isw = lambda s: bool(re.fullmatch(r"[A-Za-z0-9_]+", s))
def inv(mp):
    d = {}
    for k in ("map", "identity_map", "sub_map"):
        for a, b in (mp.get(k) or {}).items():
            if isinstance(b, str): d.setdefault(b, a)
    return d
oi = {r: inv(v) for r, v in O["maps"].items()}; ni = {r: inv(v) for r, v in N["maps"].items()}
def recoded(w, a):  # same word after the sub-token inverse (compound names)
    parts = re.split(r"(_+)", w)
    return "".join(a.get(p, p) for p in parts)
cat = collections.Counter(); samples = collections.defaultdict(collections.Counter)
differ = changed_real = changed_opaque = n = 0; per_task = set(); same_sha = dict(old=0, new=0, total=0); lengths_diff = 0
for tid in sorted(set(O["prompts"]) & set(N["prompts"])):
    repo = nt[tid]["repo"]; a, b = oi[repo], ni[repo]
    for key in sorted(set(O["prompts"][tid]) & set(N["prompts"][tid])):
        n += 1; x, y = O["prompts"][tid][key], N["prompts"][tid][key]
        same_sha["total"] += 1
        same_sha["old"] += O["sha"][tid][key] == ot[tid]["prompt_sha256"][key]
        same_sha["new"] += N["sha"][tid][key] == nt[tid]["prompt_sha256"][key]
        if x == y: continue
        differ += 1; per_task.add(tid)
        if key.startswith("real"): changed_real += 1
        else: changed_opaque += 1
        p, q = W.findall(x), W.findall(y)
        if len(p) != len(q):
            lengths_diff += 1
        sm = difflib.SequenceMatcher(None, p, q, autojunk=False) if len(p) != len(q) else None
        ops = sm.get_opcodes() if sm else [("replace", i, i + 1, i, i + 1) for i in range(len(p)) if p[i] != q[i]]
        for tag, i1, i2, j1, j2 in ops:
            if tag == "equal": continue
            pp, qq = p[i1:i2], q[j1:j2]
            if len(pp) != len(qq):
                cat["unaligned_span"] += 1; continue
            for s, t in zip(pp, qq):
                if s == t: continue
                if not (isw(s) and isw(t)):
                    c = "other_nonword"
                elif "user" in (s, t) and p[max(i1 - 1, 0)].endswith("@"):
                    c = "handle"
                elif a.get(s) is not None and a.get(s) == b.get(t):
                    c = "same_name_new_pseudoword"
                elif recoded(s, a) == recoded(t, b) and (recoded(s, a) != s or recoded(t, b) != t):
                    c = "same_name_new_pseudoword"
                elif a.get(s) == t or recoded(s, a) == t:
                    c = "was_renamed_now_kept"
                elif b.get(t) == s or recoded(t, b) == s:
                    c = "was_kept_now_renamed"
                elif a.get(s) is not None and b.get(t) is not None:
                    c = "two_different_source_names"
                else:
                    c = "other_word"
                cat[c] += 1
                if c != "same_name_new_pseudoword": samples[c][(a.get(s) or s) + " -> " + (b.get(t) or t)] += 1
res = dict(prompts_compared=n, prompts_differ=differ, tasks_with_a_difference=len(per_task), real_prompts_differ=changed_real, opaque_prompts_differ=changed_opaque,
           prompts_with_changed_token_count=lengths_diff, categories=dict(cat), dump_sha_matches_frozen=same_sha,
           samples={k: dict(v.most_common(40)) for k, v in samples.items()})
json.dump(res, open(out, "w"), indent=1, sort_keys=True); print(json.dumps(res)[:3000])
