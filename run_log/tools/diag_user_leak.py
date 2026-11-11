# Read-only: where the hard-leak token "user" sits in the opaque/none/1 prompt of 3 Django tasks. Our package only.
import json, os, re, sys
P = sys.argv[1]; PKG = os.path.join(P, "gemma4-paper-code"); sys.path.insert(0, os.path.join(PKG, "src"))
from ngraph import lite, rename as rn, studyb as sb
IDS = ["django__django-12125", "django__django-15202", "django__django-16229"]
src = lite.LiteSource(P + "/lite/swebench_lite_test.jsonl", P + "/lite-repos", P + "/lite/swebench_lite_dev.jsonl")
got = {}; orig = sb.render_task
def cap(rec, task, index, renamer, count, *a, **k):
    r = orig(rec, task, index, renamer, count, *a, **k)
    got[rec["task_id"]] = (r["prompts"][("opaque", "none", 1)], task, renamer)
    return r
sb.render_task = cap
sb.build_records(src, "lite", sb.vocab_counter(os.path.join(PKG, "third_party/llama.cpp/ggml-vocab-gemma-4.gguf")), IDS, log=lambda x: None)
def to_orig(spans, k):
    last = None
    for os_, oe, ns, ne in spans:
        if ns <= k < ne: return os_, oe
        if ne <= k: last = (oe, ne)
    return (k, k + 1) if last is None else (k - last[1] + last[0], k - last[1] + last[0] + 1)
out = {}
for tid in IDS:
    p, task, rr = got[tid]; issue = sb.normalise_issue(task["problem_statement"]); rd = rr.rename_issue(issue)
    i0 = p.find(rd.text); cand = p.find("Candidate functions")
    dotted = rn._merge([(m.start(), m.end()) for m in rn.DOTTED_RE.finditer(p)])
    occ = []
    for m in re.finditer(r"\buser\b", p):
        s, e = m.span(); w = {"offset": s, "window": repr(p[max(0, s - 50):e + 50]), "inside_dotted": rn._inside(dotted, s), "before": repr(p[max(0, s - 1):s])}
        if i0 >= 0 and i0 <= s < i0 + len(rd.text):
            a, b = to_orig(rd.spans, s - i0); w["part"] = "issue"; w["orig_issue_window"] = repr(issue[max(0, a - 50):b + 50])
        elif s >= cand >= 0:
            hdr = [h.group(1) for h in re.finditer(r"^([A-J])\. ", p[:s], re.M)]; w["part"] = "candidate " + (hdr[-1] if hdr else "?")
        else: w["part"] = "other"
        occ.append(w)
    out[tid] = {"issue_found_in_prompt": i0 >= 0, "occurrences": occ, "leak_scan_hard": rr.leak_scan(p)["hard"]}
rr = got[IDS[0]][2]
out["renamer"] = {"user_in_map": "user" in rr.map, "maps_to": rr.map.get("user"), "user_in_renamable": "user" in rr.renamable, "user_in_protected": "user" in rr.protected, "user_in_identity_map": "user" in rr.identity_map, "user_is_a_new_name": "user" in rr.inverse, "inverse_of_user": rr.inverse.get("user") if isinstance(rr.inverse, dict) else None, "common_word": bool(rr.common("user"))}
json.dump(out, open(P + "/run_log/studyb_diag/user_leak.json", "w"), indent=1); print("OK")
