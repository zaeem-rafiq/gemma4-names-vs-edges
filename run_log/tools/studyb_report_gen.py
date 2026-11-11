# Builds run_log/studyb_build_report.md from the logs and outputs. Run with -I. Reads only our own build outputs and logs.
import hashlib, json, os, statistics as st, sys
P = sys.argv[1]; RL = P + "/run_log/"; FZ = P + "/studyb-frozen/"
def rd(p):
    with open(p, encoding="utf-8", errors="replace") as f: return f.read()
def tail(p, n=40):
    return "\n".join(l[:600] for l in rd(p).splitlines()[-n:])
L = []; w = L.append
def code(s, lang=""): w(f"```{lang}\n{s}\n```")
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
m = json.load(open(P + "/lite/fetch_meta.json")); c = json.load(open(RL + "studyb_commits.json"))
ex = dict(l.split(" exit=")[0:1] + [l.split(" exit=", 1)[1]] for l in rd(RL + "studyb_builds.exit").splitlines())
w("# Study B build report\n")
w("## Outcome\n")
w("**Blocked at step 5. Steps 1 to 4 succeeded. The Lite build failed, so `studyb-frozen/lite/` is empty.** The official build is complete: 129 tasks, 111 eligible, 0 hard leaks.\n")
w("The Lite build stopped after 122 of 317 tasks. Our renamer raises `could not find a valid opaque renaming` on matplotlib. Run alone, the same step also fails on sympy and passes on the other 12 repositories the build did not reach. These two repositories hold 100 of the 317 Lite tasks: 23 in matplotlib and 77 in sympy.\n")
w("Decision needed from you:\n")
w("1. Do you approve a code fix to the renamer and a full rebuild of both sets? I recommend yes. Without it, Lite has no task files, and I cannot build those 100 tasks. The fix changes frozen code. I would regenerate `CODE_SHA256.txt` and rebuild the official set to confirm that its hashes stay the same. You need to authorise the fix first, because I must not edit the code folder without your approval. Reply \"fix renamer\" to approve.\n")
w("Hard leaks: 3 of the 122 Lite tasks built before the crash have one, and each is the identifier `user`. The tasks are `django__django-12125`, `django__django-15202` and `django__django-16229`. Each leak appears in all 8 opaque prompt variants of its task. I did not scan the remaining 195 tasks.\n")
w("## Commands: exit codes and times (UTC)\n")
w("| Step | Command | Exit | Start | End |\n|---|---|---|---|---|")
w("| 1 | pytest tests | 1 (1 expected failure) | 2026-11-09T21:16:20Z | 2026-11-09T21:16:28Z |")
w("| 2 | lite_fetch.py attempt 1 | 1 (rows API HTTP 502/503 after 6 retries; no JSONL written) | 2026-11-09T21:16:54Z | 2026-11-09T21:18:21Z |")
w("| 2 | lite_fetch.py attempt 2 (12 retries) | 0 | 2026-11-09T21:18:33Z | 2026-11-09T21:18:39Z |")
def row(n, cmd, s):
    e, r = s.split(" start="); a, b = r.split(" end="); w(f"| {n} | {cmd} | {e} | {a} | {b} |")
row(3, "lite_clone.sh (17 clones)", rd(RL + "studyb_clone.exit").strip().split("exit=", 1)[1])
row(3, "lite_check_commits.py", rd(RL + "studyb_commits.exit").strip().split("exit=", 1)[1])
row(4, "studyb build --set official", ex["build_official"]); row(4, "studyb mc3", ex["mc3"])
if "build_lite" in ex: row(5, "studyb build --set lite", ex["build_lite"])
else: w("| 5 | studyb build --set lite | NOT FINISHED | | |")
w("\nThe first start of the two builds (official from 21:19 UTC, Lite from 21:21 UTC) was stopped by me before any output was written, because the wrapper could not capture exit codes under zsh. Those partial logs are kept as `*.aborted1`. The table shows the restarted runs, which used `run_log/tools/studyb_build.sh`.\n")
w("## Step 1: tests\n")
code(tail(RL + "studyb_pytest.log"))
w("Result: every test passes except the expected `tests/test_commit.py::test_package_code_sha256_is_current`. The 23 skipped tests are as the suite reports.\n")
w("## Step 2: SWE-bench Lite\n")
w(f"- Dataset commit sha: `{m['sha']}`. Gated: {m['gated']}. Card licence: none shown (`license` = {m['license']}).")
w(f"- File list: {', '.join(m['siblings'])}.\n- Source record: `P/lite/SOURCES.md`.\n")
w("| File | Bytes | SHA-256 | Downloaded UTC |\n|---|---|---|---|")
for k, v in m["files"].items(): w(f"| raw/{k} | {v['bytes']} | `{v['sha256']}` | {v['utc']} |")
sz = {s["split"]: s for s in m["size_api"]}
w("\n| Split | Rows (JSONL) | num_rows_total | Parquet num_rows (/size API) | JSONL bytes | JSONL SHA-256 |\n|---|---|---|---|---|---|")
for s in ("test", "dev"):
    d = m["splits"][s]; w(f"| {s} | {d['jsonl_lines']} | {d['num_rows_total']} | {sz[s]['num_rows']} | {d['jsonl_bytes']} | `{d['jsonl_sha256']}` |")
w(f"\nFields: {', '.join(m['splits']['test']['features'])} (same 12 in both splits). No row had truncated cells. Limit: pyarrow is absent, so the JSONL was not compared cell by cell with the parquet files.\n")
w("Tasks per repo:\n\n| Repo | test | dev |\n|---|---|---|")
te, de = m["splits"]["test"]["by_repo"], m["splits"]["dev"]["by_repo"]
for r in sorted(set(te) | set(de)): w(f"| {r} | {te.get(r, 0)} | {de.get(r, 0)} |")
w("\nFetch log tail:\n"); code(tail(RL + "studyb_lite_fetch.log"))
w("\n## Step 3: clones (psf/requests excluded)\n")
w("| Repo | test | dev | Clone size (KB) | Base commits found | Missing | Fetched |\n|---|---|---|---|---|---|---|")
for r, v in c["repos"].items(): w(f"| {r} | {v['test']} | {v['dev']} | {v['size_kb']} | {v['found']} | {v['missing']} | {v['fetched']} |")
tot = c["repos"].values()
w(f"\nTotals: {sum(v['found'] for v in tot)} base commits found, {sum(v['missing'] for v in tot)} missing, {len(c['missing_events'])} fetches attempted. Clones use {c['total_kb']} KB. Free space at the check: `{c['free']}`.\n")
code(tail(RL + "studyb_clone.log"))
def med(xs): return st.median(xs) if xs else None
def build(name, logf):
    d = FZ + name + "/"
    w(f"\n## Build: {name}\n")
    if not os.path.exists(d + "tasks.json"):
        w("**FAILED: exit 1. No output files were written to `studyb-frozen/lite/`, so there is no summary, params block or graph table for Lite.**\n")
        log = rd(RL + logf)
        w(f"Tasks completed before the failure: {log.count('eligible=')} of 317 (astropy, django, marshmallow). The crash came on the first matplotlib task.\n")
        w("Log tail (last 40 lines):\n"); code(tail(RL + logf))
        dg = RL + "studyb_diag/"
        w("\n### Diagnosis (read-only; outputs in `run_log/studyb_diag/`; no file in PKG was changed)\n")
        w("Observed in `run_log/studyb_diag/renamer2.log`, for the names that failed all 100 tries of `OpaqueNamer.fit` in `src/ngraph/rename.py`:\n")
        w("| Repo | Name | Composed new name | Why rejected | Distinct new names in 100 tries |\n|---|---|---|---|---|")
        w("| matplotlib/matplotlib | `''` (empty) | `b` | already a name in the repo (`taken_names`) | 1 |")
        for a, b in (("a11", "f11"), ("a1_", "f1_"), ("a2_", "f2_")): w(f"| sympy/sympy | `{a}` | `{b}` | already a name in the repo (`taken_names`) | 1 |")
        w("\nCause, inferred from those numbers and from reading `fit` and `_draw`: the name's one-letter sub-token is redrawn after each rejection, but the redraw returned the same letter every time. That fits the 26 one-letter pseudo-words all being in use, so the only free letter is the one just released. `_draw` returns that letter and never reaches its longer-word fallback, so `fit` repeats the same rejected name until it gives up. I did not instrument `_pseudo_word` to prove the pool is full.\n")
        w("Why matplotlib reaches this path: `collect_names` takes the top-level package from `mod.split('.')[0]`. The file `.circleci/fetch_doc_logs.py` gets the module name `.circleci.fetch_doc_logs`, so the first component is the empty string and it joins `names.identity`. `shape('')` gives the placeholder sub-token `x`. xarray and scikit-learn also have the empty name and pass, so the empty name alone is not fatal. sympy has the empty name too, but its reported failures are `a11`, `a1_` and `a2_`.\n")
        e = json.load(open(dg + "empty_module.json"))
        w("Files with an empty module component (matplotlib only was scanned for this):\n"); code(json.dumps(e, indent=1), "json")
        r = json.load(open(dg + "renamer.json"))
        w("Same renamer step run alone on every repository the build did not reach (seed 1, all base commits):\n\n| Repo | Renamer result |\n|---|---|")
        w("| matplotlib/matplotlib | RuntimeError: could not find a valid opaque renaming |")
        for k, v in r.items(): w(f"| {k} | {v['result']} |")
        lk = {}
        for sub in ("django16229", "django_leaks"):
            t = json.load(open(dg + sub + "/tasks.json"))
            lk.update({x["task_id"]: x["hard_leaks"] for x in t["tasks"] if x.get("hard_leaks")})
        n = sum(1 for l in log.splitlines() if "leaks=" in l and not l.rstrip().endswith("leaks=0"))
        w(f"\nHard leaks seen before the crash: {n} of the 122 logged tasks have leaks > 0. Reruns with `--only` (output in `run_log/studyb_diag/django16229/` and `django_leaks/`) give the lists below. These are diagnostic runs, not frozen outputs. Tasks after the crash point were not scanned.\n")
        code(json.dumps(lk, indent=1), "json")
        return
    t = json.load(open(d + "tasks.json")); g = json.load(open(d + "graphs_report.json"))
    w("Summary:\n"); code(json.dumps(t["summary"], indent=1), "json")
    w("`params` block of tasks.json:\n"); code(json.dumps(t["params"], indent=1), "json")
    w("Output files:\n\n| File | Bytes | SHA-256 |\n|---|---|---|")
    for f in sorted(os.listdir(d)): w(f"| {f} | {os.path.getsize(d + f)} | `{sha(d + f)}` |")
    hl = {x["task_id"]: x["hard_leaks"] for x in t["tasks"] if x.get("hard_leaks")}
    w(f"\nTasks with hard leaks: {len(hl)}.")
    for k, v in hl.items(): w(f"- {k}: {json.dumps(v)}")
    fails = []; rows = []
    for gn, r in g.items():
        s = r.get("stats", {}); rw = r.get("rewired", {}); wm = r.get("within_module") or {}
        inv = rw.get("invariants") or {}
        rows.append(dict(mirrored=s.get("mirrored"), self_loops=s.get("self_loops"), dup=s.get("duplicate_edges_dropped"), ov=rw.get("edge_overlap"), wov=wm.get("edge_overlap"), ok=inv.get("all_ok"), wok=(wm.get("invariants") or {}).get("all_ok")))
        if not (rw.get("completed") and inv.get("all_ok") and rw.get("error") is None):
            fails.append({"graph": gn, "rewired": {k: rw.get(k) for k in ("completed", "error", "edge_overlap")}, "invariants": inv})
        if wm and not (wm.get("completed") and (wm.get("invariants") or {}).get("all_ok")):
            fails.append({"graph": gn, "within_module": {k: wm.get(k) for k in ("completed", "edge_overlap")}, "invariants": wm.get("invariants")})
    nn = lambda k: [x[k] for x in rows if isinstance(x[k], (int, float))]
    w(f"\nGraphs in graphs_report.json: {len(rows)}.\n")
    w("| Measure | Value |\n|---|---|")
    w(f"| mirrored = true / false / absent | {sum(x['mirrored'] is True for x in rows)} / {sum(x['mirrored'] is False for x in rows)} / {sum(x['mirrored'] is None for x in rows)} |")
    for lab, k in (("self_loops", "self_loops"), ("duplicate_edges_dropped", "dup"), ("rewired edge_overlap", "ov"), ("within_module edge_overlap", "wov")):
        v = nn(k); w(f"| {lab}: median / min / max (n={len(v)}) | {med(v)} / {min(v) if v else None} / {max(v) if v else None} |")
    w(f"| rewired invariants pass / fail / absent | {sum(x['ok'] is True for x in rows)} / {sum(x['ok'] is False for x in rows)} / {sum(x['ok'] is None for x in rows)} |")
    w(f"| within_module invariants pass / fail / absent | {sum(x['wok'] is True for x in rows)} / {sum(x['wok'] is False for x in rows)} / {sum(x['wok'] is None for x in rows)} |")
    w(f"\nFailures (rewiring not completed, error, or an invariant false): {len(fails)}.")
    for f in fails[:60]: w(f"- {json.dumps(f)}")
    if len(fails) > 60: w(f"- ... {len(fails) - 60} more; see graphs_report.json")
    w("\nLog tail (last 40 lines):\n"); code(tail(RL + logf))
build("official", "studyb_build_official.log")
w("\n## mc3.json\n")
mc = json.load(open(FZ + "official/mc3.json"))
ks = ["repo", "graph", "official_library_functions", "our_nodes", "common_nodes", "official_pairs", "our_pairs", "common_pairs", "ours_in_official", "official_in_ours"]
w("| Task | " + " | ".join(ks) + " |\n|---|" + "---|" * len(ks))
for t, v in mc.items(): w(f"| {t} | " + " | ".join(str(round(v[k], 4) if isinstance(v[k], float) else v[k]) for k in ks) + " |")
w("\nLog tail (last 40 lines):\n"); code(tail(RL + "studyb_mc3.log"))
build("lite", "studyb_build_lite.log")
open(RL + "studyb_build_report.md", "w").write("\n".join(L) + "\n")
print(len("\n".join(L).encode()), "bytes")
